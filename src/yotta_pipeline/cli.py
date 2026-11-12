"""Command-line interface for generation, execution, and inspection."""

from __future__ import annotations

import argparse
import json
import logging
from dataclasses import asdict
from pathlib import Path

from .generator import generate_dataset
from .pipeline import PipelineConfig, run_pipeline


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="YottaFlex orders batch pipeline")
    subparsers = parser.add_subparsers(dest="command", required=True)

    generate = subparsers.add_parser("generate", help="generate reproducible CSV source data")
    generate.add_argument("--output-dir", type=Path, required=True)
    generate.add_argument("--customers", type=int, default=1_000)
    generate.add_argument("--orders", type=int, default=100_000)
    generate.add_argument("--seed", type=int, default=6282)
    generate.add_argument("--invalid-rate", type=float, default=0.01)

    run = subparsers.add_parser("run", help="run the transactional batch pipeline")
    run.add_argument("--customers", type=Path, required=True)
    run.add_argument("--orders", type=Path, required=True)
    run.add_argument("--output-dir", type=Path, default=Path("output"))
    run.add_argument("--database", type=Path)
    return parser


def main(argv: list[str] | None = None) -> int:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    args = build_parser().parse_args(argv)
    if args.command == "generate":
        result = generate_dataset(
            args.output_dir, args.customers, args.orders, args.seed, args.invalid_rate
        )
    else:
        result = asdict(
            run_pipeline(
                PipelineConfig(args.customers, args.orders, args.output_dir, args.database)
            )
        )
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
