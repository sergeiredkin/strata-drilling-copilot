# ADR 0002 — Static mode is the primary target; API serves the same export
Status: accepted (2026-10-09)
Context: the outreach link must always work without a backend or API key.
Decision: all analytics are precomputed into `data/export`; StaticSource reads it from `public/data`; the API
serves the same files in P0 (plus copilot and replay). No on-request recomputation in P0.
Consequences: identical numbers in both modes; copilot in static mode is limited to recorded sessions.
