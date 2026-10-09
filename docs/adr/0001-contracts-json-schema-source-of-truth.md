# ADR 0001 — JSON Schema is the single source of truth for contracts
Status: accepted (2026-10-09)
Context: front end and pipeline/backend are built in parallel by one agent; shapes must not drift.
Decision: `contracts/schemas/strata.schema.json` defines every payload; TS types, zod and Pydantic are generated.
Consequences: schema edits first; CI fails on stale generated code; fixtures validated against the schema.
