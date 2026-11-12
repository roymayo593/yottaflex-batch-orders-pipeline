# AI interaction record

Tool: OpenAI Codex (GPT-5 family)  
Session date: 12 November 2026  
Responses: omitted (the candidate FAQ states that responses are optional)

## Consolidated technical brief

The detailed requirements originated in the official YottaFlex challenge. After the
initial implementation, the candidate supplied a more technical prompt set to make the
AI-assisted workflow easier to reproduce. The following consolidated brief is aligned
with the code that was actually delivered; it is not presented as a verbatim chronology.

### 1. Architecture and contracts

Design a dependency-light Python and SQLite batch pipeline for `customers.csv` and
`orders.csv`. Define exact source schemas, primary keys, nullability, the customer-order
relationship, target tables, lineage fields, and a reviewable project structure.

### 2. Validation policy

Define deterministic customer and order rules for required fields, IDs, timestamps,
email/country normalization, status values, currencies, amount bounds, duplicates, and
referential integrity. Separate row-level quarantine outcomes from batch-level schema
contract failures.

### 3. Reproducible data generation

Create a fixed-seed generator with configurable customer/order counts and invalid-rate.
Support a quick sample plus at least 100,000 orders. Inject deterministic invalid amounts,
statuses, currencies, and customer references without placing answer labels in the input.

### 4. Traceable quarantine

Validate exact headers and row values. Store rejected rows with `run_id`, entity,
`source_file`, source row number, raw record, reason codes, and rejection time. Preserve
malformed rows, null keys, duplicates, and invalid references for diagnosis.

### 5. Deterministic transformation and history

Normalize fields, derive `amount_usd` using documented fixed rates, keep the latest
`updated_at` for current customer/order tables, and retain distinct valid versions in
history so late data is not silently lost.

### 6. Idempotency and operations

Fingerprint both inputs and the pipeline version so an identical successful batch is
skipped. Record run IDs, timestamps, state, input/published/rejected/history-only counts,
duration, and failure reason. Use one transaction for atomic publishing and document
retry, restart, and backfill behavior.

### 7. Automated edge-case tests

Test the happy path, header-only empty batch, malformed rows, unexpected schema,
duplicates, null keys, invalid customer references, negative amounts, invalid statuses,
timestamp ordering, deterministic conversion, late data, failed-run correction, and
identical reruns.

### 8. Reconciliation evidence

Produce per-run metrics, rejects, curated snapshots, and reconciliation showing that
input rows balance to published, rejected, and history-only outcomes. Include sample SQL
for run status, reject distribution, orphan checks, aggregates, and history versions.

### 9. Performance evidence

Generate 10,000 customers and 100,000 orders with a fixed seed, time generation and
pipeline execution, record accepted/rejected counts, identify the transaction boundary as
the primary optimization, and document the next scaling step.

### 10. Reviewer documentation

Write setup/run instructions, architecture, data dictionary, naming conventions,
assumptions, limitations, operational recovery, performance evidence, design trade-offs,
AI-use disclosure, and a complete interaction record.

## Outcome and verification

- Python standard-library runtime with SQLite persistence and CSV/JSON evidence.
- 18 automated tests passed; lint passed.
- The sample batch reconciled and an identical rerun returned `skipped`.
- A seeded 100,000-order run completed in 2.09 seconds with 99,000 published and
  1,000 deliberately invalid rows quarantined.
- Five meaningful commits were published without secrets or generated runtime data.


## Supplied source files

- `YottaFlex AI Candidate Project Submission Guidelines.pdf`
- `YottaFlex AI Candidate Project-FAQ.pdf`
