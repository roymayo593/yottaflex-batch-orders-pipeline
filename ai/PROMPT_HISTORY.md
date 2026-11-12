# AI-Assisted Engineering Prompt Record

Candidate: Soumyadeep Roy  
Tool: OpenAI Codex  
Project: YottaFlex Batch Orders Pipeline

## Disclosure

Codex was used as an engineering assistant for implementation, testing, documentation, and review. The candidate supplied the official requirements, directed the delivery process, evaluated the resulting design, and retained responsibility for validation, explanation, and submission.

The prompts below are a consolidated technical record reconstructed from the official requirements and completed implementation. They are not represented as a verbatim chronological transcript.

## Prompt 1 — Architecture and Source Contracts

Help me design a locally runnable batch pipeline using Python and SQLite. It must ingest customers.csv and orders.csv, validate both files, quarantine invalid rows, preserve lineage, and publish curated customer and order tables. Define the exact source columns, data types, primary keys, nullability, customer-to-order relationship, and project structure.

## Prompt 2 — Validation Policy

Define deterministic validation rules for customer_id, order_id, full_name, email, country_code, order timestamps, update timestamps, status, amount, currency, duplicates, and customer referential integrity. Separate normalization rules, row-level rejection rules, and batch-level schema failures.

## Prompt 3 — Reproducible Data Generator

Implement a fixed-seed synthetic-data generator with configurable customer count, order count, seed, and invalid-record rate. It should support at least 100,000 orders and deterministically inject negative amounts, invalid statuses, unsupported currencies, and invalid customer references.

## Prompt 4 — Traceable Quarantine

Implement validation that checks exact CSV headers and individual row values. Rejected records must retain run_id, entity, source_file, source_row, raw_record, reason_codes, and rejected_at so every invalid record remains traceable to its source.


## Prompt 5 — Idempotency and Recovery

Make identical reruns safe by hashing the customer file, order file, and pipeline version. If an identical batch already succeeded, return the original run ID without creating duplicates. Record run status, timestamps, input counts, published counts, rejected counts, history-only counts, duration, and failure reason. Use a transaction so batch failures cannot partially publish data.

## Prompt 6 — Automated Testing

Create pytest coverage for the happy path, header-only empty input, malformed rows, null identifiers, duplicates, invalid customer references, unexpected schema changes, negative amounts, invalid statuses, timestamp ordering, deterministic currency conversion, late data, corrected retries, reproducible generation, and identical reruns.

## Prompt 7 — Reconciliation and Performance

Generate per-run metrics, reject output, curated CSV snapshots, and a reconciliation report proving that source rows are accounted for as published, rejected, or history-only. Run a seeded benchmark using 10,000 customers and 100,000 orders. Document execution time, accepted and rejected counts, the transaction optimization, and the next scaling improvement.


## Verification Results

- 18 automated tests passed.
- Static lint checks passed.
- The sample batch reconciled successfully.
- Reprocessing the identical sample returned status=skipped without duplicates.
- A seeded run containing 10,000 customers and 100,000 orders completed in approximately 2.09 seconds.
- The large run published 10,000 customers and 99,000 orders and quarantined 1,000 deliberately invalid orders.
- No secrets or generated runtime data were committed.
