"""Source schema declarations and deterministic business rules."""

from __future__ import annotations

import re
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from typing import Any

CUSTOMER_FIELDS = ("customer_id", "full_name", "email", "country_code", "updated_at")
ORDER_FIELDS = (
    "order_id",
    "customer_id",
    "order_ts",
    "status",
    "amount",
    "currency",
    "updated_at",
)

ORDER_STATUSES = {"pending", "completed", "cancelled", "refunded"}
FX_TO_USD = {
    "USD": Decimal("1.0000"),
    "EUR": Decimal("1.0800"),
    "GBP": Decimal("1.2700"),
    "INR": Decimal("0.0120"),
}
EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]{0,63}$")


@dataclass(frozen=True)
class ValidationResult:
    record: dict[str, Any] | None
    errors: tuple[str, ...]


def parse_iso8601(value: str) -> datetime:
    """Parse an ISO-8601 value and normalize it to an aware UTC datetime."""
    cleaned = value.strip().replace("Z", "+00:00")
    parsed = datetime.fromisoformat(cleaned)
    if parsed.tzinfo is None:
        raise ValueError("timezone is required")
    return parsed.astimezone(timezone.utc)


def iso_utc(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def validate_customer(row: Mapping[str, str | None]) -> ValidationResult:
    errors: list[str] = []
    customer_id = (row.get("customer_id") or "").strip()
    full_name = (row.get("full_name") or "").strip()
    email = (row.get("email") or "").strip().lower()
    country_code = (row.get("country_code") or "").strip().upper()
    updated_raw = (row.get("updated_at") or "").strip()

    if not customer_id:
        errors.append("null_customer_id")
    elif not ID_RE.fullmatch(customer_id):
        errors.append("invalid_customer_id")
    if not full_name:
        errors.append("missing_full_name")
    if not EMAIL_RE.fullmatch(email):
        errors.append("invalid_email")
    if len(country_code) != 2 or not country_code.isalpha():
        errors.append("invalid_country_code")
    try:
        updated_at = parse_iso8601(updated_raw)
    except (ValueError, TypeError):
        errors.append("invalid_updated_at")
        updated_at = None

    if errors:
        return ValidationResult(None, tuple(errors))
    return ValidationResult(
        {
            "customer_id": customer_id,
            "full_name": full_name,
            "email": email,
            "country_code": country_code,
            "updated_at": iso_utc(updated_at),
        },
        (),
    )


def validate_order(row: Mapping[str, str | None]) -> ValidationResult:
    errors: list[str] = []
    order_id = (row.get("order_id") or "").strip()
    customer_id = (row.get("customer_id") or "").strip()
    status = (row.get("status") or "").strip().lower()
    currency = (row.get("currency") or "").strip().upper()
    amount_raw = (row.get("amount") or "").strip()

    if not order_id:
        errors.append("null_order_id")
    elif not ID_RE.fullmatch(order_id):
        errors.append("invalid_order_id")
    if not customer_id:
        errors.append("null_customer_id")
    elif not ID_RE.fullmatch(customer_id):
        errors.append("invalid_customer_id")
    if status not in ORDER_STATUSES:
        errors.append("invalid_status")
    if currency not in FX_TO_USD:
        errors.append("unsupported_currency")

    try:
        amount = Decimal(amount_raw).quantize(Decimal("0.01"))
        if amount < 0:
            errors.append("negative_amount")
        if amount > Decimal("1000000.00"):
            errors.append("amount_above_limit")
    except (InvalidOperation, ValueError):
        errors.append("invalid_amount")
        amount = None

    try:
        order_ts = parse_iso8601((row.get("order_ts") or "").strip())
    except (ValueError, TypeError):
        errors.append("invalid_order_ts")
        order_ts = None
    try:
        updated_at = parse_iso8601((row.get("updated_at") or "").strip())
    except (ValueError, TypeError):
        errors.append("invalid_updated_at")
        updated_at = None

    if order_ts and updated_at and updated_at < order_ts:
        errors.append("updated_before_order")

    if errors:
        return ValidationResult(None, tuple(errors))

    amount_usd = (amount * FX_TO_USD[currency]).quantize(Decimal("0.01"))
    return ValidationResult(
        {
            "order_id": order_id,
            "customer_id": customer_id,
            "order_ts": iso_utc(order_ts),
            "status": status,
            "amount": f"{amount:.2f}",
            "currency": currency,
            "amount_usd": f"{amount_usd:.2f}",
            "updated_at": iso_utc(updated_at),
        },
        (),
    )
