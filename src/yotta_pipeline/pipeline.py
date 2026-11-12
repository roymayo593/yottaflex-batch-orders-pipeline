"""Transactional, idempotent batch pipeline implementation."""

from __future__ import annotations

import csv
import hashlib
import json
import logging
import sqlite3
import time
import uuid
from collections import defaultdict
from collections.abc import Callable, Iterable, Mapping
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .schema import (
    CUSTOMER_FIELDS,
    ORDER_FIELDS,
    ValidationResult,
    validate_customer,
    validate_order,
)
from .storage import connect

LOGGER = logging.getLogger("yotta_pipeline")


@dataclass(frozen=True)
class PipelineConfig:
    customers_csv: Path
    orders_csv: Path
    output_dir: Path
    database_path: Path | None = None

    def resolved_database_path(self) -> Path:
        return self.database_path or self.output_dir / "pipeline.db"


@dataclass(frozen=True)
class PipelineResult:
    run_id: str
    status: str
    batch_fingerprint: str
    customers_input: int
    customers_published: int
    orders_input: int
    orders_published: int
    history_only_count: int
    rejected_count: int
    duration_seconds: float
    database_path: str
    message: str = ""


@dataclass(frozen=True)
class SourceRecord:
    source_file: str
    source_row: int
    raw: dict[str, Any]
    parsed: dict[str, Any]


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _file_digest(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def batch_fingerprint(customers_csv: Path, orders_csv: Path) -> str:
    digest = hashlib.sha256()
    digest.update(b"yotta-pipeline-v1\0")
    for entity, path in (("customers", customers_csv), ("orders", orders_csv)):
        digest.update(entity.encode())
        digest.update(b"\0")
        digest.update(_file_digest(path).encode())
        digest.update(b"\0")
    return digest.hexdigest()


def _stable_hash(record: Mapping[str, Any]) -> str:
    payload = json.dumps(record, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return hashlib.sha256(payload.encode()).hexdigest()


def _read_and_validate(
    path: Path,
    entity: str,
    expected_fields: tuple[str, ...],
    validator: Callable[[Mapping[str, str | None]], ValidationResult],
    reject: Callable[[str, str, int, Mapping[str, Any], Iterable[str]], None],
) -> tuple[list[SourceRecord], int]:
    records: list[SourceRecord] = []
    input_count = 0
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        actual = tuple(reader.fieldnames or ())
        if actual != expected_fields:
            raise ValueError(
                f"unexpected_schema:{entity}:expected={list(expected_fields)}:actual={list(actual)}"
            )
        for row_number, row in enumerate(reader, start=2):
            input_count += 1
            if None in row:
                reject(entity, path.name, row_number, row, ("malformed_row",))
                continue
            result = validator(row)
            if result.errors:
                reject(entity, path.name, row_number, row, result.errors)
                continue
            records.append(SourceRecord(path.name, row_number, dict(row), result.record or {}))
    return records, input_count


def _deduplicate(
    records: list[SourceRecord],
    entity: str,
    key_name: str,
    reject: Callable[[str, str, int, Mapping[str, Any], Iterable[str]], None],
) -> list[SourceRecord]:
    by_key: dict[str, list[SourceRecord]] = defaultdict(list)
    for record in records:
        by_key[str(record.parsed[key_name])].append(record)

    winners: list[SourceRecord] = []
    for key in sorted(by_key):
        candidates = sorted(
            by_key[key], key=lambda item: (item.parsed["updated_at"], item.source_row)
        )
        winner = candidates[-1]
        winners.append(winner)
        for duplicate in candidates[:-1]:
            reject(
                entity,
                duplicate.source_file,
                duplicate.source_row,
                duplicate.raw,
                ("duplicate_key_in_batch", f"superseded_by_row_{winner.source_row}"),
            )
    return winners


def _export_query(connection: sqlite3.Connection, query: str, path: Path) -> int:
    cursor = connection.execute(query)
    rows = cursor.fetchall()
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        fields = [column[0] for column in cursor.description]
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        if rows:
            writer.writerows(dict(row) for row in rows)
    return len(rows)


def _write_json(path: Path, data: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _publish_customer(connection: sqlite3.Connection, record: SourceRecord, run_id: str) -> bool:
    data = record.parsed
    record_hash = _stable_hash(data)
    connection.execute(
        """INSERT OR IGNORE INTO customer_history
           (customer_id, full_name, email, country_code, updated_at, source_file,
            source_row, run_id, record_hash)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            data["customer_id"],
            data["full_name"],
            data["email"],
            data["country_code"],
            data["updated_at"],
            record.source_file,
            record.source_row,
            run_id,
            record_hash,
        ),
    )
    existing = connection.execute(
        "SELECT updated_at FROM customers_curated WHERE customer_id = ?", (data["customer_id"],)
    ).fetchone()
    if existing and existing["updated_at"] > data["updated_at"]:
        return False
    connection.execute(
        """INSERT INTO customers_curated
           (customer_id, full_name, email, country_code, updated_at, source_file, source_row, run_id)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?)
           ON CONFLICT(customer_id) DO UPDATE SET
             full_name=excluded.full_name, email=excluded.email,
             country_code=excluded.country_code, updated_at=excluded.updated_at,
             source_file=excluded.source_file, source_row=excluded.source_row, run_id=excluded.run_id
           WHERE excluded.updated_at >= customers_curated.updated_at""",
        (
            data["customer_id"],
            data["full_name"],
            data["email"],
            data["country_code"],
            data["updated_at"],
            record.source_file,
            record.source_row,
            run_id,
        ),
    )
    return True


def _publish_order(connection: sqlite3.Connection, record: SourceRecord, run_id: str) -> bool:
    data = record.parsed
    record_hash = _stable_hash(data)
    connection.execute(
        """INSERT OR IGNORE INTO order_history
           (order_id, customer_id, order_ts, status, amount, currency, amount_usd,
            updated_at, source_file, source_row, run_id, record_hash)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            data["order_id"],
            data["customer_id"],
            data["order_ts"],
            data["status"],
            data["amount"],
            data["currency"],
            data["amount_usd"],
            data["updated_at"],
            record.source_file,
            record.source_row,
            run_id,
            record_hash,
        ),
    )
    existing = connection.execute(
        "SELECT updated_at FROM orders_curated WHERE order_id = ?", (data["order_id"],)
    ).fetchone()
    if existing and existing["updated_at"] > data["updated_at"]:
        return False
    connection.execute(
        """INSERT INTO orders_curated
           (order_id, customer_id, order_ts, status, amount, currency, amount_usd,
            updated_at, source_file, source_row, run_id)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
           ON CONFLICT(order_id) DO UPDATE SET
             customer_id=excluded.customer_id, order_ts=excluded.order_ts,
             status=excluded.status, amount=excluded.amount, currency=excluded.currency,
             amount_usd=excluded.amount_usd, updated_at=excluded.updated_at,
             source_file=excluded.source_file, source_row=excluded.source_row, run_id=excluded.run_id
           WHERE excluded.updated_at >= orders_curated.updated_at""",
        (
            data["order_id"],
            data["customer_id"],
            data["order_ts"],
            data["status"],
            data["amount"],
            data["currency"],
            data["amount_usd"],
            data["updated_at"],
            record.source_file,
            record.source_row,
            run_id,
        ),
    )
    return True


def run_pipeline(config: PipelineConfig) -> PipelineResult:
    """Run one atomic batch and export review-friendly artifacts."""
    started_clock = time.perf_counter()
    config.output_dir.mkdir(parents=True, exist_ok=True)
    database_path = config.resolved_database_path()
    fingerprint = batch_fingerprint(config.customers_csv, config.orders_csv)
    connection = connect(database_path)

    prior = connection.execute(
        "SELECT * FROM pipeline_runs WHERE batch_fingerprint = ? AND status = 'succeeded'",
        (fingerprint,),
    ).fetchone()
    if prior:
        connection.close()
        return PipelineResult(
            run_id=prior["run_id"],
            status="skipped",
            batch_fingerprint=fingerprint,
            customers_input=prior["customers_input"],
            customers_published=prior["customers_published"],
            orders_input=prior["orders_input"],
            orders_published=prior["orders_published"],
            history_only_count=prior["history_only_count"],
            rejected_count=prior["rejected_count"],
            duration_seconds=round(time.perf_counter() - started_clock, 6),
            database_path=str(database_path),
            message="identical batch already succeeded",
        )

    run_id = str(uuid.uuid4())
    started_at = utc_now()
    metrics: dict[str, int] = {
        "customers_input": 0,
        "customers_published": 0,
        "orders_input": 0,
        "orders_published": 0,
        "history_only_count": 0,
        "rejected_count": 0,
    }

    def reject(
        entity: str,
        source_file: str,
        source_row: int,
        raw_record: Mapping[str, Any],
        reasons: Iterable[str],
    ) -> None:
        metrics["rejected_count"] += 1
        connection.execute(
            """INSERT INTO rejects
               (run_id, entity, source_file, source_row, raw_record, reason_codes, rejected_at)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (
                run_id,
                entity,
                source_file,
                source_row,
                json.dumps(
                    {str(key): value for key, value in raw_record.items()},
                    sort_keys=True,
                    default=str,
                ),
                "|".join(reasons),
                utc_now(),
            ),
        )

    try:
        connection.execute("BEGIN")
        connection.execute(
            "INSERT INTO pipeline_runs (run_id, batch_fingerprint, status, started_at) VALUES (?, ?, 'running', ?)",
            (run_id, fingerprint, started_at),
        )
        customers, metrics["customers_input"] = _read_and_validate(
            config.customers_csv, "customer", CUSTOMER_FIELDS, validate_customer, reject
        )
        customers = _deduplicate(customers, "customer", "customer_id", reject)
        for customer in customers:
            published = _publish_customer(connection, customer, run_id)
            metrics["customers_published"] += int(published)
            metrics["history_only_count"] += int(not published)

        orders, metrics["orders_input"] = _read_and_validate(
            config.orders_csv, "order", ORDER_FIELDS, validate_order, reject
        )
        orders = _deduplicate(orders, "order", "order_id", reject)
        known_customers = {
            row[0] for row in connection.execute("SELECT customer_id FROM customers_curated")
        }
        for order in orders:
            if order.parsed["customer_id"] not in known_customers:
                reject(
                    "order",
                    order.source_file,
                    order.source_row,
                    order.raw,
                    ("invalid_customer_reference",),
                )
                continue
            published = _publish_order(connection, order, run_id)
            metrics["orders_published"] += int(published)
            metrics["history_only_count"] += int(not published)

        ended_at = utc_now()
        connection.execute(
            """UPDATE pipeline_runs SET status='succeeded', ended_at=?,
               customers_input=?, customers_published=?, orders_input=?, orders_published=?,
               history_only_count=?, rejected_count=? WHERE run_id=?""",
            (
                ended_at,
                metrics["customers_input"],
                metrics["customers_published"],
                metrics["orders_input"],
                metrics["orders_published"],
                metrics["history_only_count"],
                metrics["rejected_count"],
                run_id,
            ),
        )
        connection.commit()
    except Exception as exc:
        connection.rollback()
        connection.execute(
            """INSERT OR REPLACE INTO pipeline_runs
               (run_id, batch_fingerprint, status, started_at, ended_at, failure_reason)
               VALUES (?, ?, 'failed', ?, ?, ?)""",
            (run_id, fingerprint, started_at, utc_now(), str(exc)),
        )
        connection.commit()
        connection.close()
        raise

    run_dir = config.output_dir / "runs" / run_id
    curated_dir = config.output_dir / "curated"
    _export_query(
        connection,
        "SELECT * FROM customers_curated ORDER BY customer_id",
        curated_dir / "customers_curated.csv",
    )
    _export_query(
        connection,
        "SELECT * FROM orders_curated ORDER BY order_id",
        curated_dir / "orders_curated.csv",
    )
    _export_query(
        connection,
        f"SELECT entity, source_file, source_row, raw_record, reason_codes, rejected_at "
        f"FROM rejects WHERE run_id = '{run_id}' ORDER BY reject_id",
        run_dir / "rejects.csv",
    )

    customer_total = connection.execute("SELECT COUNT(*) FROM customers_curated").fetchone()[0]
    order_total = connection.execute("SELECT COUNT(*) FROM orders_curated").fetchone()[0]
    order_value_usd = connection.execute(
        "SELECT COALESCE(ROUND(SUM(CAST(amount_usd AS REAL)), 2), 0) FROM orders_curated"
    ).fetchone()[0]
    reconciliation = {
        "run_id": run_id,
        "customers": {
            "input": metrics["customers_input"],
            "valid_after_dedup": metrics["customers_published"],
            "curated_total": customer_total,
        },
        "orders": {
            "input": metrics["orders_input"],
            "valid_after_dedup_and_fk": metrics["orders_published"],
            "curated_total": order_total,
            "curated_amount_usd": order_value_usd,
        },
        "rejected_count": metrics["rejected_count"],
        "history_only_count": metrics["history_only_count"],
        "run_balance_check": (
            metrics["customers_input"] + metrics["orders_input"]
            == metrics["customers_published"]
            + metrics["orders_published"]
            + metrics["history_only_count"]
            + metrics["rejected_count"]
        ),
        "notes": "Published counts exclude older late-arriving versions retained only in history.",
    }
    _write_json(run_dir / "reconciliation.json", reconciliation)

    duration = round(time.perf_counter() - started_clock, 6)
    result = PipelineResult(
        run_id=run_id,
        status="succeeded",
        batch_fingerprint=fingerprint,
        duration_seconds=duration,
        database_path=str(database_path),
        **metrics,
    )
    _write_json(run_dir / "metrics.json", asdict(result))
    connection.close()
    LOGGER.info("run_id=%s status=succeeded duration_seconds=%.6f", run_id, duration)
    return result
