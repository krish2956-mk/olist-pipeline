"""
db_config.py — Centralized Database Configuration
===================================================
This is the SINGLE SOURCE OF TRUTH for the database connection.
All modules in this project import `get_connection()` from here.

To migrate to a different database, change the DB_URL and the
`get_connection()` implementation below — nothing else needs to change.

Supported Databases
-------------------
SQLite (default, zero setup):
    DB_URL = "sqlite:///ecommerce.db"
    Driver:  built-in (no extra install needed)

PostgreSQL:
    DB_URL = "postgresql+psycopg2://user:password@host:5432/dbname"
    Install: pip install psycopg2-binary sqlalchemy

MySQL / MariaDB:
    DB_URL = "mysql+pymysql://user:password@host:3306/dbname"
    Install: pip install pymysql sqlalchemy

Microsoft SQL Server:
    DB_URL = "mssql+pyodbc://user:password@host/dbname?driver=ODBC+Driver+17+for+SQL+Server"
    Install: pip install pyodbc sqlalchemy

Google BigQuery:
    DB_URL = "bigquery://project-id/dataset"
    Install: pip install sqlalchemy-bigquery google-cloud-bigquery
"""

import os
import sqlite3
from contextlib import contextmanager
from dotenv import load_dotenv
from sqlalchemy import create_engine

load_dotenv()  # Load environment variables from .env file

# ── Configuration ─────────────────────────────────────────────────────────────
# Read from environment variable if set, otherwise default to local SQLite.
# To switch databases, set the DB_URL environment variable or change the
# default value below.
DB_URL = os.environ.get("DB_URL", "sqlite")

# For SQLite: path to the .db file (relative to project root or absolute).
SQLITE_DB_PATH = os.environ.get(
    "SQLITE_DB_PATH",
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "ecommerce.db"),
)


# ── Connection Factory ────────────────────────────────────────────────────────
def get_connection(db_path: str = None):
    """
    Returns a database connection object.

    For SQLite, `db_path` overrides SQLITE_DB_PATH (useful for tests or
    Airflow where the path differs from the project root).

    For other databases (PostgreSQL, MySQL, etc.), this function should be
    updated to return a SQLAlchemy engine or a driver-specific connection.

    Usage:
        conn = get_connection()
        df = pd.read_sql_query("SELECT ...", conn)
        conn.close()

    Or use the context manager version for automatic cleanup:
        with db_connection() as conn:
            df = pd.read_sql_query("SELECT ...", conn)
    """
    # ── SQLite (default) ──────────────────────────────────────────────────────
    if DB_URL == "sqlite" or DB_URL.startswith("sqlite"):
        path = db_path or SQLITE_DB_PATH
        return sqlite3.connect(path)

    # ── SQLAlchemy-backed databases (PostgreSQL, MySQL, BigQuery, etc.) ───────
    engine = create_engine(DB_URL)
    return engine.connect()


@contextmanager
def db_connection(db_path: str = None):
    """
    Context-manager wrapper around get_connection().
    Automatically closes the connection when the `with` block exits.

    Usage:
        with db_connection() as conn:
            df = pd.read_sql_query("SELECT * FROM orders", conn)
    """
    conn = get_connection(db_path)
    try:
        yield conn
    finally:
        conn.close()
