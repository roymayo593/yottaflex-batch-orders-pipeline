# AI use disclosure

AI assistance was used transparently and substantially for this submission.

## Tool

- OpenAI Codex, GPT-5 family, used on 12 November 2026.

## Where AI accelerated the work

- Converted the project brief into an implementation checklist.
- Proposed the Python/SQLite vertical-slice architecture.
- Generated the initial source modules, tests, sample data, and documentation.
- Diagnosed test and packaging issues and suggested corrections.
- Helped design edge-case coverage and reconciliation evidence.

## Candidate direction, judgment, and ownership

The candidate selected the task, supplied the authenticated official brief and repository
context, chose a transparent AI-assisted delivery workflow, and directed the work toward
a complete, reproducible submission. The candidate retained responsibility for what would
be published and submitted. No other person implemented the solution.

Codex proposed Python and SQLite after reading the constraints. That proposal was retained
because it met the candidate's practical goal: a dependency-light vertical slice that a
reviewer can run locally. Architectural decisions, assumptions, limitations, and measured
evidence are made explicit throughout the repository so they can be challenged and
explained rather than hidden behind generated code.

## Validation performed

- 18 automated tests were executed locally, including failures, retry, idempotency,
  schema drift, malformed data, duplicates, nulls, late data, and referential integrity.
- Static lint checks were executed locally.
- The sample batch was run twice to verify both reconciliation and rerun safety.
- A seeded 100,000-order workload was generated and processed in 2.09 seconds.
- The repository was checked for generated files and common secret patterns before publication.

This is intentionally an AI-assisted engineering submission, not a claim that every line
was typed manually. The ownership signal is the explicit reasoning, reproducible evidence,
test coverage, and willingness to explain or modify the system during review.

AI responses are not included because the guidelines make them optional. All user
prompts submitted in this Codex work session are recorded in `PROMPT_HISTORY.md`.
