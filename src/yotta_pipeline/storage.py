"""SQLite target schema and publishing helpers."""

from __future__ import annotations

import sqlite3
from pathlib import Path

DDL = """
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS pipeline_runs (
    run_id TEXT PRIMARY KEY,
    batch_fingerprint TEXT NOT NULL,
    status TEXT NOT NULL CHECK (status IN ('running', 'succeeded', 'failed')),
    started_at TEXT NOT NULL,
    ended_at TEXT,
    customers_input INTEGER NOT NULL DEFAULT 0,
    customers_published INTEGER NOT NULL DEFAULT 0,
    orders_input INTEGER NOT NULL DEFAULT 0,
    orders_published INTEGER NOT NULL DEFAULT 0,
    history_only_count INTEGER NOT NULL DEFAULT 0,
    rejected_count INTEGER NOT NULL DEFAULT 0,
    failure_reason TEXT,
    UNIQUE(batch_fingerprint, status)
);

CREATE TABLE IF NOT EXISTS customers_curated (
    customer_id TEXT PRIMARY KEY,
    full_name TEXT NOT NULL,
    email TEXT NOT NULL,
    country_code TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    source_file TEXT NOT NULL,
    source_row INTEGER NOT NULL,
    run_id TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS customer_history (
    customer_id TEXT NOT NULL,
    full_name TEXT NOT NULL,
    email TEXT NOT NULL,
    country_code TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    source_file TEXT NOT NULL,
    source_row INTEGER NOT NULL,
    run_id TEXT NOT NULL,
    record_hash TEXT NOT NULL,
    PRIMARY KEY (customer_id, updated_at, record_hash)
);

CREATE TABLE IF NOT EXISTS orders_curated (
    order_id TEXT PRIMARY KEY,
    customer_id TEXT NOT NULL,
    order_ts TEXT NOT NULL,
    status TEXT NOT NULL,
    amount TEXT NOT NULL,
    currency TEXT NOT NULL,
    amount_usd TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    source_file TEXT NOT NULL,
    source_row INTEGER NOT NULL,
    run_id TEXT NOT NULL,
    FOREIGN KEY (customer_id) REFERENCES customers_curated(customer_id)
);

CREATE TABLE IF NOT EXISTS order_history (
    order_id TEXT NOT NULL,
    customer_id TEXT NOT NULL,
    order_ts TEXT NOT NULL,
    status TEXT NOT NULL,
    amount TEXT NOT NULL,
    currency TEXT NOT NULL,
    amount_usd TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    source_file TEXT NOT NULL,
    source_row INTEGER NOT NULL,
    run_id TEXT NOT NULL,
    record_hash TEXT NOT NULL,
    PRIMARY KEY (order_id, updated_at, record_hash)
);

CREATE TABLE IF NOT EXISTS rejects (
    reject_id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id TEXT NOT NULL,
    entity TEXT NOT NULL,
    source_file TEXT NOT NULL,
    source_row INTEGER NOT NULL,
    raw_record TEXT NOT NULL,
    reason_codes TEXT NOT NULL,
    rejected_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_rejects_run ON rejects(run_id);
CREATE INDEX IF NOT EXISTS idx_orders_customer ON orders_curated(customer_id);
"""


def connect(path: Path) -> sqlite3.Connection:
    path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(path)
    connection.row_factory = sqlite3.Row
    connection.executescript(DDL)
    return connection
