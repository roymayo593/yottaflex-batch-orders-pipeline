# Operations guide

## Run lifecycle

1. Compute a SHA-256 fingerprint of both files and pipeline version.
2. Return `skipped` if that fingerprint already succeeded.
3. Create a `running` run record and begin one transaction.
4. Validate customers, publish them, then validate and publish orders.
5. Commit targets, rejects, and successful metrics together.
6. Export CSV snapshots and per-run JSON/CSV evidence.

## Failure and retry

Schema mismatch or unexpected execution failure rolls back the batch. A separate failed
run record captures the reason. Correct the source/configuration and rerun. A changed
file creates a new fingerprint. An unchanged failed file is also retryable; successful
fingerprints alone are skipped.

## Backfill

Run historical file pairs in chronological order when possible. Out-of-order execution
is safe: an older `updated_at` is history-only and cannot overwrite a newer curated row.

## Monitoring signals

- `pipeline_runs.status` and `failure_reason`
- run duration and source/published/rejected/history-only counts
- rejection rate and reason-code distribution
- `run_balance_check` in reconciliation output
- curated row counts and USD aggregate

Suggested alerts: failed run; unexpected schema; rejection rate above an agreed
threshold; run balance false; duration or source volume outside normal bounds.

## Recovery boundaries

SQLite is authoritative. If CSV export fails after the database commit, rerunning the
same batch returns `skipped`; regenerate snapshots from the curated tables or remove only
the derived export directory. Do not delete the database when preserving run history.

