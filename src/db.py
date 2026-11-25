"""Database connection and raw-layer helpers for PostgreSQL."""

from __future__ import annotations

import os
from typing import Any

import psycopg2
from dotenv import load_dotenv
from psycopg2 import sql
from psycopg2.extensions import connection as PgConnection
from sqlalchemy import create_engine
from sqlalchemy.engine import URL, Engine

load_dotenv()


def get_db_config() -> dict[str, Any]:
    """Return PostgreSQL connection parameters loaded from environment variables."""
    return {
        "host": os.getenv("POSTGRES_HOST", "localhost"),
        "port": int(os.getenv("POSTGRES_PORT", "5434")),
        "dbname": os.getenv("POSTGRES_DB", "olist_dw"),
        "user": os.getenv("POSTGRES_USER", "olist_user"),
        "password": os.getenv("POSTGRES_PASSWORD", "olist_dev_password"),
    }


def get_connection() -> PgConnection:
    """Open a new psycopg2 connection to the configured PostgreSQL database."""
    cfg = get_db_config()
    return psycopg2.connect(**cfg)


def get_sqlalchemy_engine() -> Engine:
    """Create a SQLAlchemy engine for the configured PostgreSQL database."""
    cfg = get_db_config()
    url = URL.create(
        drivername="postgresql+psycopg2",
        username=cfg["user"],
        password=cfg["password"],
        host=cfg["host"],
        port=cfg["port"],
        database=cfg["dbname"],
    )
    return create_engine(url, pool_pre_ping=True)


def ensure_raw_schema(conn: PgConnection) -> None:
    """Create the immutable `raw` schema if it does not already exist."""
    with conn.cursor() as cur:
        cur.execute("CREATE SCHEMA IF NOT EXISTS raw;")
    conn.commit()


def get_raw_table_counts(conn: PgConnection) -> list[tuple[str, int]]:
    """Return `(table_name, row_count)` sorted alphabetically for all tables in `raw`."""
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT table_name
            FROM information_schema.tables
            WHERE table_schema = 'raw'
              AND table_type = 'BASE TABLE'
            ORDER BY table_name;
            """
        )
        tables = [row[0] for row in cur.fetchall()]

        counts: list[tuple[str, int]] = []
        for table_name in tables:
            cur.execute(
                sql.SQL("SELECT COUNT(*) FROM {}.{}").format(
                    sql.Identifier("raw"),
                    sql.Identifier(table_name),
                )
            )
            row_count = int(cur.fetchone()[0])
            counts.append((table_name, row_count))

    return counts
