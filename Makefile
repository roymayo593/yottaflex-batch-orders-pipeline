.PHONY: install test lint sample generate-large clean

install:
	python -m pip install -e ".[dev]"

test:
	pytest

lint:
	ruff check src tests

sample:
	yotta-pipeline run --customers sample_data/input/customers.csv --orders sample_data/input/orders.csv --output-dir output/sample

generate-large:
	yotta-pipeline generate --output-dir output/generated --customers 10000 --orders 100000 --seed 6282 --invalid-rate 0.01

clean:
	python -c "from pathlib import Path; import shutil; p=Path('output'); shutil.rmtree(p) if p.exists() else None; p.mkdir()"

