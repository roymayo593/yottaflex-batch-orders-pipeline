"""Deterministic synthetic source-data generator."""

from __future__ import annotations

import csv
import random
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from .schema import CUSTOMER_FIELDS, ORDER_FIELDS

FIRST_NAMES = ("Aarav", "Aisha", "Elena", "Liam", "Mei", "Noah", "Priya", "Sofia")
LAST_NAMES = ("Brown", "Chen", "Garcia", "Khan", "Patel", "Roy", "Singh", "Smith")
COUNTRIES = ("IN", "US", "GB", "DE", "SG")
CURRENCIES = ("INR", "USD", "GBP", "EUR")
STATUSES = ("pending", "completed", "cancelled", "refunded")


def _iso(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def _write(path: Path, fields: tuple[str, ...], rows: list[dict[str, Any]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def generate_dataset(
    output_dir: Path,
    customers: int = 1_000,
    orders: int = 100_000,
    seed: int = 6282,
    invalid_rate: float = 0.01,
) -> dict[str, Any]:
    if customers < 1 or orders < 0:
        raise ValueError("customers must be >= 1 and orders must be >= 0")
    if not 0 <= invalid_rate <= 0.25:
        raise ValueError("invalid_rate must be between 0 and 0.25")

    output_dir.mkdir(parents=True, exist_ok=True)
    randomizer = random.Random(seed)
    base = datetime(2026, 1, 1, tzinfo=timezone.utc)

    customer_rows: list[dict[str, Any]] = []
    for index in range(1, customers + 1):
        first = randomizer.choice(FIRST_NAMES)
        last = randomizer.choice(LAST_NAMES)
        customer_rows.append(
            {
                "customer_id": f"C{index:08d}",
                "full_name": f"{first} {last}",
                "email": f"{first.lower()}.{last.lower()}.{index}@example.test",
                "country_code": randomizer.choice(COUNTRIES),
                "updated_at": _iso(base + timedelta(minutes=index)),
            }
        )

    order_rows: list[dict[str, Any]] = []
    invalid_count = round(orders * invalid_rate)
    invalid_indices = set(randomizer.sample(range(orders), invalid_count)) if orders else set()
    for index in range(orders):
        customer_index = randomizer.randint(1, customers)
        order_ts = base + timedelta(minutes=randomizer.randint(0, 525_600))
        updated_at = order_ts + timedelta(minutes=randomizer.randint(0, 10_000))
        row = {
            "order_id": f"O{index + 1:010d}",
            "customer_id": f"C{customer_index:08d}",
            "order_ts": _iso(order_ts),
            "status": randomizer.choice(STATUSES),
            "amount": f"{randomizer.uniform(0, 10_000):.2f}",
            "currency": randomizer.choice(CURRENCIES),
            "updated_at": _iso(updated_at),
        }
        if index in invalid_indices:
            choice = index % 4
            if choice == 0:
                row["amount"] = "-1.00"
            elif choice == 1:
                row["status"] = "lost"
            elif choice == 2:
                row["customer_id"] = "C99999999"
            else:
                row["currency"] = "XYZ"
        order_rows.append(row)

    customers_path = output_dir / "customers.csv"
    orders_path = output_dir / "orders.csv"
    _write(customers_path, CUSTOMER_FIELDS, customer_rows)
    _write(orders_path, ORDER_FIELDS, order_rows)
    return {
        "customers_path": str(customers_path),
        "orders_path": str(orders_path),
        "customers": customers,
        "orders": orders,
        "deliberately_invalid_orders": invalid_count,
        "seed": seed,
    }
