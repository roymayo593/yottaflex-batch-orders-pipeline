from __future__ import annotations

import json
import sqlite3

import pytest
from conftest import CUSTOMER_FIELDS, ORDER_FIELDS, write_csv

from yotta_pipeline.pipeline import PipelineConfig, run_pipeline


def setup_batch(tmp_path, customer_rows, order_rows):
    customers = write_csv(tmp_path / "input" / "customers.csv", CUSTOMER_FIELDS, customer_rows)
    orders = write_csv(tmp_path / "input" / "orders.csv", ORDER_FIELDS, order_rows)
    return PipelineConfig(customers, orders, tmp_path / "output")


def test_happy_path_publishes_and_reconciles(tmp_path, valid_customer, valid_order):
    result = run_pipeline(setup_batch(tmp_path, [valid_customer], [valid_order]))
    assert result.status == "succeeded"
    assert result.customers_published == 1
    assert result.orders_published == 1
    assert result.rejected_count == 0
    reconciliation = json.loads(
        (tmp_path / "output" / "runs" / result.run_id / "reconciliation.json").read_text()
    )
    assert reconciliation["run_balance_check"]
    assert reconciliation["run_id"] == result.run_id


def test_header_only_empty_batch_succeeds(tmp_path):
    result = run_pipeline(setup_batch(tmp_path, [], []))
    assert result.status == "succeeded"
    assert result.customers_input == result.orders_input == 0


def test_invalid_rows_are_traceable(tmp_path, valid_customer, valid_order):
    invalid = dict(valid_order, amount="-1.00")
    result = run_pipeline(setup_batch(tmp_path, [valid_customer], [invalid]))
    assert result.rejected_count == 1
    db = sqlite3.connect(result.database_path)
    row = db.execute("SELECT source_row, reason_codes, raw_record FROM rejects").fetchone()
    assert row[0] == 2
    assert "negative_amount" in row[1]
    assert '"order_id": "O001"' in row[2]


def test_duplicate_latest_record_wins(tmp_path, valid_customer, valid_order):
    newer = dict(valid_order, status="refunded", updated_at="2026-01-03T00:00:00Z")
    result = run_pipeline(setup_batch(tmp_path, [valid_customer], [valid_order, newer]))
    assert result.rejected_count == 1
    db = sqlite3.connect(result.database_path)
    assert db.execute("SELECT status FROM orders_curated").fetchone()[0] == "refunded"


def test_invalid_reference_is_rejected(tmp_path, valid_customer, valid_order):
    orphan = dict(valid_order, customer_id="C999")
    result = run_pipeline(setup_batch(tmp_path, [valid_customer], [orphan]))
    assert result.orders_published == 0
    assert result.rejected_count == 1


def test_identical_rerun_is_skipped_without_duplicates(tmp_path, valid_customer, valid_order):
    config = setup_batch(tmp_path, [valid_customer], [valid_order])
    first = run_pipeline(config)
    second = run_pipeline(config)
    assert second.status == "skipped"
    assert second.run_id == first.run_id
    db = sqlite3.connect(first.database_path)
    assert db.execute("SELECT COUNT(*) FROM orders_curated").fetchone()[0] == 1
    assert db.execute("SELECT COUNT(*) FROM pipeline_runs").fetchone()[0] == 1


def test_schema_drift_fails_and_records_failure(tmp_path, valid_customer, valid_order):
    customers = write_csv(
        tmp_path / "input" / "customers.csv",
        CUSTOMER_FIELDS + ["new_column"],
        [dict(valid_customer, new_column="x")],
    )
    orders = write_csv(tmp_path / "input" / "orders.csv", ORDER_FIELDS, [valid_order])
    config = PipelineConfig(customers, orders, tmp_path / "output")
    with pytest.raises(ValueError, match="unexpected_schema"):
        run_pipeline(config)
    db = sqlite3.connect(config.resolved_database_path())
    status, reason = db.execute("SELECT status, failure_reason FROM pipeline_runs").fetchone()
    assert status == "failed"
    assert "unexpected_schema" in reason


def test_failed_schema_can_be_corrected_and_retried(tmp_path, valid_customer, valid_order):
    customers = write_csv(
        tmp_path / "input/customers.csv",
        CUSTOMER_FIELDS + ["unexpected"],
        [dict(valid_customer, unexpected="drift")],
    )
    orders = write_csv(tmp_path / "input/orders.csv", ORDER_FIELDS, [valid_order])
    config = PipelineConfig(customers, orders, tmp_path / "output")
    with pytest.raises(ValueError, match="unexpected_schema"):
        run_pipeline(config)

    write_csv(customers, CUSTOMER_FIELDS, [valid_customer])
    retry = run_pipeline(config)
    assert retry.status == "succeeded"
    db = sqlite3.connect(config.resolved_database_path())
    assert db.execute("SELECT COUNT(*) FROM customers_curated").fetchone()[0] == 1
    assert db.execute("SELECT COUNT(*) FROM orders_curated").fetchone()[0] == 1


def test_late_older_update_is_preserved_but_not_current(tmp_path, valid_customer, valid_order):
    config = setup_batch(tmp_path, [valid_customer], [valid_order])
    first = run_pipeline(config)
    newer = dict(valid_order, status="refunded", updated_at="2026-01-05T00:00:00Z")
    write_csv(config.orders_csv, ORDER_FIELDS, [newer])
    run_pipeline(config)
    older = dict(valid_order, status="pending", updated_at="2026-01-03T00:00:00Z")
    write_csv(config.orders_csv, ORDER_FIELDS, [older])
    third = run_pipeline(config)
    db = sqlite3.connect(first.database_path)
    assert db.execute("SELECT status FROM orders_curated").fetchone()[0] == "refunded"
    assert db.execute("SELECT COUNT(*) FROM order_history").fetchone()[0] == 3
    assert third.orders_published == 0
    assert third.history_only_count == 1


def test_malformed_extra_column_is_rejected(tmp_path, valid_customer):
    customers = write_csv(tmp_path / "input" / "customers.csv", CUSTOMER_FIELDS, [valid_customer])
    orders = tmp_path / "input" / "orders.csv"
    orders.write_text(
        ",".join(ORDER_FIELDS)
        + "\nO1,C001,2026-01-02T00:00:00Z,completed,10,USD,2026-01-02T01:00:00Z,EXTRA\n"
    )
    result = run_pipeline(PipelineConfig(customers, orders, tmp_path / "output"))
    assert result.rejected_count == 1
    assert result.orders_published == 0
