# ADR 0004 — Confidence and evidence are produced only by the pipeline
Status: accepted (2026-10-09)
Decision: `pipeline/confidence.py` is the only confidence implementation; every exported number gets an
evidence record. The UI renders, never derives. Copilot tools return the same objects.
