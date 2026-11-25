"""Idempotent ingestion of the 9 official Olist CSV datasets into `raw`."""

from __future__ import annotations

import argparse
import csv
import logging
import os
import shutil
import sys
import zipfile
from pathlib import Path

from dotenv import load_dotenv
from psycopg2 import sql
from psycopg2.extensions import connection as PgConnection

if __package__ is None or __package__ == "":
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.db import ensure_raw_schema, get_connection

load_dotenv()

logger = logging.getLogger(__name__)

KAGGLE_DATASET_SLUG = "olistbr/brazilian-ecommerce"
KAGGLE_DATASET_URL = "https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce"

OLIST_TABLES: dict[str, str] = {
    "olist_customers_dataset.csv": "olist_customers",
    "olist_geolocation_dataset.csv": "olist_geolocation",
    "olist_order_items_dataset.csv": "olist_order_items",
    "olist_order_payments_dataset.csv": "olist_order_payments",
    "olist_order_reviews_dataset.csv": "olist_order_reviews",
    "olist_orders_dataset.csv": "olist_orders",
    "olist_products_dataset.csv": "olist_products",
    "olist_sellers_dataset.csv": "olist_sellers",
    "product_category_name_translation.csv": "product_category_name_translation",
}


def extract_local_zips(data_dir: Path) -> None:
    """Extract any Olist ZIP files placed in `data/raw/` or `data/raw/olist/`."""
    data_dir.mkdir(parents=True, exist_ok=True)
    parent_dir = data_dir.parent
    zip_files = sorted(list(parent_dir.glob("*.zip")) + list(data_dir.glob("*.zip")))
    for zip_path in zip_files:
        logger.info("Extracting local archive %s into %s", zip_path, data_dir)
        with zipfile.ZipFile(zip_path, "r") as zf:
            for member in zf.infolist():
                filename = Path(member.filename).name
                if filename in OLIST_TABLES and not member.is_dir():
                    target = data_dir / filename
                    with zf.open(member) as src_fh, target.open("wb") as dst_fh:
                        shutil.copyfileobj(src_fh, dst_fh)


def find_missing_csvs(data_dir: Path) -> list[str]:
    """Return any required Olist CSV filenames missing from `data_dir`."""
    return [fname for fname in OLIST_TABLES if not (data_dir / fname).is_file()]


def download_olist_dataset(data_dir: Path) -> None:
    """Download the real Olist dataset via kagglehub and place all 9 CSVs in `data_dir`."""
    data_dir.mkdir(parents=True, exist_ok=True)
    try:
        import kagglehub
    except ImportError as exc:
        raise RuntimeError(
            "kagglehub is not installed. Run `pip install -r requirements.txt`."
        ) from exc

    logger.info("Downloading official Olist dataset (%s) via kagglehub...", KAGGLE_DATASET_SLUG)
    downloaded_path = Path(kagglehub.dataset_download(KAGGLE_DATASET_SLUG))
    logger.info("kagglehub cache directory: %s", downloaded_path)

    available_files = {p.name: p for p in downloaded_path.rglob("*.csv")}
    copied = 0
    for csv_name in OLIST_TABLES:
        target = data_dir / csv_name
        if target.is_file():
            continue
        source = available_files.get(csv_name)
        if source is None:
            raise FileNotFoundError(
                f"Expected file '{csv_name}' was not found inside kagglehub download at {downloaded_path}"
            )
        shutil.copy2(source, target)
        copied += 1

    logger.info("Copied %d Olist CSV files into %s", copied, data_dir.resolve())


def _read_csv_headers(csv_path: Path) -> list[str]:
    """Read raw CSV headers stripping UTF-8 BOM without altering column names."""
    with csv_path.open("r", encoding="utf-8-sig", newline="") as fh:
        reader = csv.reader(fh)
        try:
            headers = next(reader)
        except StopIteration as exc:
            raise ValueError(f"CSV file is empty: {csv_path}") from exc

    cleaned = [col.strip() for col in headers]
    if not cleaned or any(not col for col in cleaned):
        raise ValueError(f"Invalid empty header in CSV file: {csv_path}")
    return cleaned


def load_olist_csv_to_raw(conn: PgConnection, csv_path: Path, table_name: str) -> int:
    """Load one Olist CSV immutably into `raw.<table_name>` using PostgreSQL COPY."""
    headers = _read_csv_headers(csv_path)
    table_ident = sql.Identifier("raw", table_name)

    source_col_defs = [sql.SQL("{} TEXT").format(sql.Identifier(col)) for col in headers]
    all_col_defs = source_col_defs + [
        sql.SQL("_ingested_at TIMESTAMPTZ NOT NULL DEFAULT NOW()"),
        sql.SQL("_source_file TEXT NOT NULL DEFAULT {}").format(sql.Literal(csv_path.name)),
    ]

    create_stmt = sql.SQL("CREATE TABLE IF NOT EXISTS {} ({});").format(
        table_ident,
        sql.SQL(", ").join(all_col_defs),
    )
    truncate_stmt = sql.SQL("TRUNCATE TABLE {};").format(table_ident)
    copy_cols = sql.SQL(", ").join(sql.Identifier(col) for col in headers)
    copy_stmt = sql.SQL(
        "COPY {} ({}) FROM STDIN WITH (FORMAT csv, HEADER true, NULL '');"
    ).format(table_ident, copy_cols)

    with conn.cursor() as cur:
        cur.execute(create_stmt)
        cur.execute(truncate_stmt)
        with csv_path.open("r", encoding="utf-8-sig", newline="") as fh:
            cur.copy_expert(copy_stmt.as_string(conn), fh)
        cur.execute(sql.SQL("SELECT COUNT(*) FROM {};").format(table_ident))
        row_count = int(cur.fetchone()[0])

    conn.commit()
    logger.info("Loaded %s rows into raw.%s from %s", f"{row_count:,}", table_name, csv_path.name)
    return row_count


def ingest_olist(skip_download: bool = False) -> dict[str, int]:
    """Ensure all 9 Olist CSVs exist locally and load them idempotently into `raw`."""
    data_dir = Path(os.getenv("OLIST_DATA_DIR", "data/raw/olist"))
    extract_local_zips(data_dir)
    missing = find_missing_csvs(data_dir)

    if missing and not skip_download:
        try:
            download_olist_dataset(data_dir)
        except Exception as exc:
            logger.error("Automatic Olist download failed: %s", exc)
            print(
                "\n[ACTION REQUIRED] No se pudieron descargar automáticamente los 9 CSVs reales de Olist.\n"
                f"1. Descargá el ZIP oficial desde: {KAGGLE_DATASET_URL}\n"
                f"2. Descomprimí los 9 archivos CSV (o dejá el .zip) en: {data_dir.resolve()}\n"
                "3. Volvé a ejecutar: python src/ingest_olist.py\n",
                file=sys.stderr,
            )
            raise

    still_missing = find_missing_csvs(data_dir)
    if still_missing:
        print(
            "\n[ACTION REQUIRED] Faltan archivos CSV reales de Olist en "
            f"{data_dir.resolve()}: {', '.join(still_missing)}\n"
            f"Descargalos desde {KAGGLE_DATASET_URL} y volvé a ejecutar: python src/ingest_olist.py\n",
            file=sys.stderr,
        )
        raise FileNotFoundError(
            f"Faltan archivos CSV de Olist en {data_dir.resolve()}: {', '.join(still_missing)}"
        )

    results: dict[str, int] = {}
    conn = get_connection()
    try:
        ensure_raw_schema(conn)
        for csv_name, table_name in OLIST_TABLES.items():
            csv_path = data_dir / csv_name
            results[table_name] = load_olist_csv_to_raw(conn, csv_path, table_name)
    finally:
        conn.close()

    return results


def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )
    parser = argparse.ArgumentParser(description="Ingest Olist CSV files into raw schema.")
    parser.add_argument(
        "--skip-download",
        "--no-download",
        dest="skip_download",
        action="store_true",
        help="Do not attempt kagglehub download; require CSVs to already exist locally.",
    )
    args = parser.parse_args()
    results = ingest_olist(skip_download=args.skip_download)
    for table, count in results.items():
        print(f"raw.{table}: {count:,} rows")


if __name__ == "__main__":
    main()
