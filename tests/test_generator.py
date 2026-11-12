from pathlib import Path

from yotta_pipeline.generator import generate_dataset


def test_generator_is_reproducible(tmp_path):
    first = tmp_path / "first"
    second = tmp_path / "second"
    generate_dataset(first, customers=10, orders=100, seed=42, invalid_rate=0.1)
    generate_dataset(second, customers=10, orders=100, seed=42, invalid_rate=0.1)
    assert (first / "customers.csv").read_bytes() == (second / "customers.csv").read_bytes()
    assert (first / "orders.csv").read_bytes() == (second / "orders.csv").read_bytes()


def test_generator_supports_large_configurable_volume(tmp_path):
    result = generate_dataset(tmp_path, customers=100, orders=1_000, seed=1, invalid_rate=0.02)
    assert result["customers"] == 100
    assert result["orders"] == 1_000
    assert result["deliberately_invalid_orders"] == 20
    assert Path(result["orders_path"]).exists()
