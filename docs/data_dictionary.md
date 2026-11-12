# Data dictionary

## Source: customers

Grain: one customer version per source row. Natural key: `customer_id`.

| Column | Type | Nullable | Rule |
|---|---|---:|---|
| `customer_id` | string | No | 1-64 stable ID characters: letters, digits, `_`, `-` |
| `full_name` | string | No | Trimmed, non-empty |
| `email` | string | No | Basic email-shape validation; normalized lowercase |
| `country_code` | string | No | Two letters; normalized uppercase |
| `updated_at` | timestamp | No | Timezone-aware ISO-8601; normalized to UTC |

## Source: orders

Grain: one order-state version per source row. Natural key: `order_id`.
`customer_id` is a foreign key to the current customer table.

| Column | Type | Nullable | Rule |
|---|---|---:|---|
| `order_id` | string | No | Same stable-ID rule as customers |
| `customer_id` | string | No | Must resolve to a curated customer |
| `order_ts` | timestamp | No | Timezone-aware ISO-8601 |
| `status` | enum | No | `pending`, `completed`, `cancelled`, `refunded` |
| `amount` | decimal(12,2) | No | 0 through 1,000,000 inclusive |
| `currency` | enum | No | USD, EUR, GBP, INR |
| `updated_at` | timestamp | No | Must be on or after `order_ts` |

## Curated additions

| Column | Table(s) | Meaning |
|---|---|---|
| `amount_usd` | orders | `amount * fixed_fx_rate`, rounded to two decimals |
| `source_file` | customers, orders | Original filename for lineage |
| `source_row` | customers, orders | One-based CSV row including header offset |
| `run_id` | all operational/target tables | UUID for the processing attempt |
| `record_hash` | history tables | SHA-256 of normalized business fields |

Fixed FX rates: USD 1.0000, EUR 1.0800, GBP 1.2700, INR 0.0120.

## Target tables

- `customers_curated`: latest accepted version per `customer_id`.
- `orders_curated`: latest accepted version per `order_id`, with enforced customer FK.
- `customer_history`: all distinct valid customer versions.
- `order_history`: all distinct valid order versions, including late older arrivals.
- `rejects`: raw source row, entity, filename, row number, reason codes, rejection time.
- `pipeline_runs`: fingerprint, state, timestamps, counts, and failure reason.

