from __future__ import annotations

import csv
from pathlib import Path

import pytest

CUSTOMER_FIELDS = ["customer_id", "full_name", "email", "country_code", "updated_at"]
ORDER_FIELDS = ["order_id", "customer_id", "order_ts", "status", "amount", "currency", "updated_at"]


def write_csv(path: Path, fields: list[str], rows: list[dict[str, str]]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)
    return path


@pytest.fixture
def valid_customer() -> dict[str, str]:
    return {
        "customer_id": "C001",
        "full_name": "Aisha Khan",
        "email": "aisha@example.test",
        "country_code": "IN",
        "updated_at": "2026-01-01T00:00:00Z",
    }


@pytest.fixture
def valid_order() -> dict[str, str]:
    return {
        "order_id": "O001",
        "customer_id": "C001",
        "order_ts": "2026-01-02T00:00:00Z",
        "status": "completed",
        "amount": "100.00",
        "currency": "USD",
        "updated_at": "2026-01-02T00:01:00Z",
    }
