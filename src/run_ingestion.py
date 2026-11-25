"""End-to-end Sprint 1 ELT ingestion entrypoint (BCB SGS API + Olist CSVs)."""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from tabulate import tabulate

from src.db import ensure_raw_schema, get_connection, get_raw_table_counts
from src.ingest_bcb import ingest_bcb
from src.ingest_olist import ingest_olist

logger = logging.getLogger(__name__)


def print_raw_summary() -> list[tuple[str, int]]:
    """Query PostgreSQL `raw` schema and print a formatted row-count summary."""
    with get_connection() as conn:
        counts = get_raw_table_counts(conn)

    table_rows = [(f"raw.{name}", f"{count:,}") for name, count in counts]
    print("\n=== PostgreSQL `raw` Schema Row Counts ===")
    print(tabulate(table_rows, headers=["Table", "Rows"], tablefmt="github"))
    print(f"\nTotal tables in raw: {len(counts)} | Total rows: {sum(c for _, c in counts):,}")
    return counts


def main() -> int:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )
    parser = argparse.ArgumentParser(description="Run full idempotent raw ingestion (BCB + Olist).")
    parser.add_argument(
        "--use-bcb-cache",
        action="store_true",
        help="Use cached BCB JSON files if present instead of calling the BCB API.",
    )
    parser.add_argument(
        "--skip-olist-download",
        action="store_true",
        help="Skip kagglehub download and read Olist CSVs from OLIST_DATA_DIR.",
    )
    parser.add_argument(
        "--bcb-only",
        action="store_true",
        help="Only run BCB SGS API ingestion.",
    )
    args = parser.parse_args()

    with get_connection() as conn:
        ensure_raw_schema(conn)

    logger.info("Step 1/2: Running BCB SGS macro series ingestion...")
    ingest_bcb(use_cache=args.use_bcb_cache)

    if not args.bcb_only:
        logger.info("Step 2/2: Running Olist CSV dataset ingestion...")
        try:
            ingest_olist(skip_download=args.skip_olist_download)
        except Exception:
            print_raw_summary()
            return 1

    print_raw_summary()
    return 0


if __name__ == "__main__":
    sys.exit(main())
