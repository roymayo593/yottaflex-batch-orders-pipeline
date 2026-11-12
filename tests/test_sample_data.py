from __future__ import annotations

import csv
from pathlib import Path

from yotta_pipeline.pipeline import PipelineConfig, run_pipeline

ROOT = Path(__file__).resolve().parents[1]


def _read_selected(path: Path, fields: list[str]) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as handle:
        return [{field: row[field] for field in fields} for row in csv.DictReader(handle)]


def test_committed_sample_matches_expected_outputs(tmp_path):
    result = run_pipeline(
        PipelineConfig(
            ROOT / "sample_data/input/customers.csv",
            ROOT / "sample_data/input/orders.csv",
            tmp_path / "output",
        )
    )
    customer_fields = ["customer_id", "full_name", "email", "country_code", "updated_at"]
    order_fields = [
        "order_id",
        "customer_id",
        "order_ts",
        "status",
        "amount",
        "currency",
        "amount_usd",
        "updated_at",
    ]
    assert _read_selected(
        tmp_path / "output/curated/customers_curated.csv", customer_fields
    ) == _read_selected(ROOT / "sample_data/expected/customers_curated.csv", customer_fields)
    assert _read_selected(
        tmp_path / "output/curated/customers_curated.csv", customer_fields
    ) == _read_selected(ROOT / "sample_data/expected/customers_curated.csv", customer_fields)
    assert _read_selected(
        tmp_path / "output/curated/orders_curated.csv", order_fields
    ) == _read_selected(ROOT / "sample_data/expected/orders_curated.csv", order_fields)
    assert result.rejected_count == 8
