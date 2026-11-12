from decimal import Decimal

from yotta_pipeline.schema import validate_customer, validate_order


def test_customer_normalization(valid_customer):
    valid_customer["email"] = "AISHA@EXAMPLE.TEST"
    valid_customer["country_code"] = "in"
    result = validate_customer(valid_customer)
    assert result.errors == ()
    assert result.record["email"] == "aisha@example.test"
    assert result.record["country_code"] == "IN"


def test_null_customer_id_is_rejected(valid_customer):
    valid_customer["customer_id"] = ""
    result = validate_customer(valid_customer)
    assert "null_customer_id" in result.errors


def test_order_derives_usd_amount(valid_order):
    valid_order["amount"] = "100.00"
    valid_order["currency"] = "GBP"
    result = validate_order(valid_order)
    assert result.errors == ()
    assert Decimal(result.record["amount_usd"]) == Decimal("127.00")


def test_domain_specific_negative_amount_and_invalid_status(valid_order):
    valid_order["amount"] = "-2"
    valid_order["status"] = "lost"
    result = validate_order(valid_order)
    assert "negative_amount" in result.errors
    assert "invalid_status" in result.errors


def test_updated_timestamp_cannot_precede_order(valid_order):
    valid_order["updated_at"] = "2025-12-01T00:00:00Z"
    result = validate_order(valid_order)
    assert "updated_before_order" in result.errors
