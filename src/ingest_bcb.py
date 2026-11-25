"""Idempotent ingestion of Central Bank of Brazil (BCB SGS) macro series into `raw`."""

from __future__ import annotations

import argparse
import json
import logging
import os
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import requests
from dotenv import load_dotenv
from psycopg2 import sql
from psycopg2.extensions import connection as PgConnection
from psycopg2.extras import execute_values
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

if __package__ is None or __package__ == "":
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.db import ensure_raw_schema, get_connection

load_dotenv()

logger = logging.getLogger(__name__)

BCB_SGS_URL_TEMPLATE = (
    "https://api.bcb.gov.br/dados/serie/bcdata.sgs.{code}/dados"
    "?formato=json&dataInicial={start_date}&dataFinal={end_date}"
)


@dataclass(frozen=True)
class BcbSeriesSpec:
    """Configuration for a single BCB SGS time series."""

    series_code: int
    table_name: str
    cache_filename: str
    description: str


BCB_SERIES: tuple[BcbSeriesSpec, ...] = (
    BcbSeriesSpec(
        series_code=433,
        table_name="bcb_ipca",
        cache_filename="bcb_sgs_433_ipca.json",
        description="IPCA monthly inflation variation (%)",
    ),
    BcbSeriesSpec(
        series_code=1,
        table_name="bcb_fx_usd_brl",
        cache_filename="bcb_sgs_1_fx_usd_brl.json",
        description="PTAX daily USD/BRL sell exchange rate",
    ),
)


def _build_retry_session() -> requests.Session:
    """Create an HTTP session configured with exponential backoff retries."""
    retry = Retry(
        total=5,
        backoff_factor=1.0,
        status_forcelist=(429, 500, 502, 503, 504),
        allowed_methods=("GET",),
        raise_on_status=False,
    )
    adapter = HTTPAdapter(max_retries=retry)
    session = requests.Session()
    session.mount("https://", adapter)
    session.mount("http://", adapter)
    session.headers.update({"Accept": "application/json", "User-Agent": "olist-elt/1.0"})
    return session


def fetch_bcb_series(
    spec: BcbSeriesSpec,
    cache_dir: Path,
    start_date: str,
    end_date: str,
    use_cache: bool = False,
) -> tuple[list[dict[str, Any]], str]:
    """Fetch BCB SGS JSON series with local cache persistence and fallback."""
    cache_dir.mkdir(parents=True, exist_ok=True)
    cache_path = cache_dir / spec.cache_filename
    source_url = BCB_SGS_URL_TEMPLATE.format(
        code=spec.series_code,
        start_date=start_date,
        end_date=end_date,
    )

    if use_cache and cache_path.exists():
        logger.info("Loading %s from local cache: %s", spec.table_name, cache_path)
        payload = json.loads(cache_path.read_text(encoding="utf-8"))
        return payload, source_url

    session = _build_retry_session()
    try:
        logger.info("Fetching BCB SGS %s (%s) from %s", spec.series_code, spec.description, source_url)
        response = session.get(source_url, timeout=30)
        response.raise_for_status()
        payload = response.json()
        if not isinstance(payload, list) or not payload:
            raise ValueError(f"Unexpected empty or non-list BCB payload for series {spec.series_code}")

        cache_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        logger.info("Cached %d records to %s", len(payload), cache_path)
        return payload, source_url
    except Exception as exc:
        if cache_path.exists():
            logger.warning(
                "BCB API request failed for series %s (%s). Falling back to local cache: %s",
                spec.series_code,
                exc,
                cache_path,
            )
            payload = json.loads(cache_path.read_text(encoding="utf-8"))
            return payload, source_url
        raise


def load_bcb_series_to_raw(
    conn: PgConnection,
    spec: BcbSeriesSpec,
    records: list[dict[str, Any]],
    source_url: str,
) -> int:
    """Idempotently replace raw BCB table contents inside a single transaction."""
    rows = [
        (str(item["data"]), str(item["valor"]), spec.series_code, source_url)
        for item in records
    ]

    table_ident = sql.Identifier("raw", spec.table_name)
    create_stmt = sql.SQL(
        """
        CREATE TABLE IF NOT EXISTS {} (
            data TEXT NOT NULL,
            valor TEXT NOT NULL,
            series_code INTEGER NOT NULL,
            _ingested_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            _source_url TEXT NOT NULL
        );
        """
    ).format(table_ident)
    truncate_stmt = sql.SQL("TRUNCATE TABLE {};").format(table_ident)
    insert_stmt = sql.SQL(
        "INSERT INTO {} (data, valor, series_code, _source_url) VALUES %s;"
    ).format(table_ident)

    with conn.cursor() as cur:
        cur.execute(create_stmt)
        cur.execute(truncate_stmt)
        execute_values(cur, insert_stmt.as_string(conn), rows, page_size=1000)
    conn.commit()
    logger.info("Loaded %d rows into raw.%s", len(rows), spec.table_name)
    return len(rows)


def ingest_bcb(use_cache: bool = False) -> dict[str, int]:
    """Run full idempotent ingestion for all configured BCB SGS series."""
    cache_dir = Path(os.getenv("BCB_DATA_DIR", "data/raw/bcb"))
    start_date = os.getenv("BCB_START_DATE", "01/08/2016")
    end_date = os.getenv("BCB_END_DATE", "31/12/2018")

    results: dict[str, int] = {}
    conn = get_connection()
    try:
        ensure_raw_schema(conn)
        for spec in BCB_SERIES:
            payload, source_url = fetch_bcb_series(
                spec=spec,
                cache_dir=cache_dir,
                start_date=start_date,
                end_date=end_date,
                use_cache=use_cache,
            )
            loaded = load_bcb_series_to_raw(conn, spec, payload, source_url)
            results[spec.table_name] = loaded
    finally:
        conn.close()
    return results


def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )
    parser = argparse.ArgumentParser(description="Ingest BCB SGS macro series into raw schema.")
    parser.add_argument(
        "--use-cache",
        action="store_true",
        help="Read series from local JSON cache if available instead of calling the API.",
    )
    args = parser.parse_args()
    results = ingest_bcb(use_cache=args.use_cache)
    for table, count in results.items():
        print(f"raw.{table}: {count} rows")


if __name__ == "__main__":
    main()
