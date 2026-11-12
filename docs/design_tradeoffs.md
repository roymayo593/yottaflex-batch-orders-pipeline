# Design decisions and trade-offs

## Why SQLite and standard-library Python

The brief asks for a complete, tested vertical slice that a reviewer can run quickly.
SQLite supplies transactions, constraints, indexes, queryability, and persistence
without infrastructure or credentials. Standard-library parsing avoids a heavy runtime
dependency for a workload where explicit rules are clearer than a dataframe abstraction.

Trade-off: this design is single-node and reads validated rows into memory for batch
deduplication. A production distributed pipeline would use object storage, a catalog,
staging tables, and set-based/streaming execution.

## Fail-closed schema drift

Headers must match exactly, including order. Silent acceptance of new or missing columns
can corrupt interpretation. Failing the run makes drift visible in `pipeline_runs`.

Trade-off: harmless additive columns also fail. A production contract could explicitly
classify additive compatible changes.

## Duplicate and late-arrival semantics

Within a batch, greatest `updated_at` wins; row number breaks ties. Across batches,
an older version is inserted into history but does not replace current state.

Trade-off: source timestamps are trusted after syntax/order validation. Production would
also monitor clock skew and may prefer a producer sequence number.

## Row rejection versus batch failure

Business-rule failures are data quality outcomes, so valid rows continue and rejects are
traceable. Contract/schema errors are batch-level failures because row interpretation is
not trustworthy. Publishing remains atomic in both cases.

## Deterministic FX conversion

Fixed rates make tests and reconciliation reproducible. They are illustrative and must
not be used for financial reporting. Production should join to a governed, effective-
dated rate table and retain the rate/version used.

## Current snapshot plus history

Current tables serve simple analytical consumers. History tables preserve all distinct
valid versions so late arrivals and changes are not silently lost. This is a pragmatic
hybrid rather than a full Type-2 dimension implementation.

