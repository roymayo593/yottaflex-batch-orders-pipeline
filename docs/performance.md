# Performance evidence

Measured on 12 November 2026 using Apple Silicon macOS and Python 3.12.

Command:

```bash
yotta-pipeline generate --output-dir output/benchmark/input \
  --customers 10000 --orders 100000 --seed 6282 --invalid-rate 0.01

yotta-pipeline run \
  --customers output/benchmark/input/customers.csv \
  --orders output/benchmark/input/orders.csv \
  --output-dir output/benchmark/result
```

Observed result:

| Metric | Value |
|---|---:|
| Generation wall time | 0.96 s |
| Pipeline internal duration | 2.093 s |
| Pipeline wall time | 2.15 s |
| Customer inputs / published | 10,000 / 10,000 |
| Order inputs / published | 100,000 / 99,000 |
| Rejected | 1,000 |

Numbers are a single local observation, not a formal benchmark. The selected optimization
is a single transaction with indexed lookups, which avoids per-row durability overhead.
The next scaling improvement is chunked validation plus set-based staging merges.

