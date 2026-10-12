"""Evidence registry — the only place `ev_<sha1>` ids are minted. `03_ARCHITECTURE.md` §5."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

Source = dict[str, Any]
Quantity = dict[str, Any]


@dataclass
class EvidenceRegistry:
    git_commit: str = "unknown"
    pipeline_version: str = "0.0.0"
    _by_id: dict[str, dict[str, Any]] = field(default_factory=dict)

    def add(
        self,
        tool: str,
        params: dict[str, Any],
        value: float | None,
        unit: str,
        sources: list[Source],
        method_note: str | None = None,
    ) -> str:
        """Registers one evidence record and returns its id. The id is a content hash of
        (tool, params, sources) so re-running the generator deterministically reuses ids."""
        key = json.dumps(
            {"tool": tool, "params": params, "sources": sources}, sort_keys=True, default=str
        )
        digest = hashlib.sha1(key.encode("utf-8")).hexdigest()[:10]
        eid = f"ev_{digest}"
        record: dict[str, Any] = {
            "id": eid,
            "tool": tool,
            "params": params,
            "value": value,
            "unit": unit,
            "sources": sources,
            "git_commit": self.git_commit,
            "generated_at": datetime.now(UTC).isoformat(),
        }
        if method_note is not None:
            record["method_note"] = method_note
        self._by_id[eid] = record
        return eid

    def quantity(
        self,
        tool: str,
        params: dict[str, Any],
        value: float | None,
        unit: str,
        sources: list[Source],
        precision: int | None = None,
        method_note: str | None = None,
    ) -> Quantity:
        """Registers evidence and returns the `Quantity` that should be embedded in the payload."""
        eid = self.add(tool, params, value, unit, sources, method_note)
        q: Quantity = {"value": value, "unit": unit, "evidence_id": eid}
        if precision is not None:
            q["precision"] = precision
        return q

    def get(self, evidence_id: str) -> dict[str, Any]:
        return self._by_id[evidence_id]

    def __len__(self) -> int:
        return len(self._by_id)

    def all_records(self) -> dict[str, dict[str, Any]]:
        """Every registered record, keyed by evidence id. For callers merging this registry's
        output with evidence already on disk from a separate export run (e.g. `generate_real.py`
        alongside `fixtures/generate.py`) rather than overwriting it — `write_shards` on its own
        only ever reflects what *this* registry instance registered."""
        return dict(self._by_id)

    def write_shards(self, out_dir: Path) -> None:
        """Writes evidence/{00..ff}.json (256 shards, keyed by the first 2 hex chars after
        `ev_`) plus evidence/shards.json (id -> shard) per `04_DATA_CONTRACTS.md` §3."""
        shards: dict[str, dict[str, Any]] = {}
        shard_of: dict[str, str] = {}
        for eid, record in self._by_id.items():
            shard = eid[3:5]
            shards.setdefault(shard, {})[eid] = record
            shard_of[eid] = shard

        shard_dir = out_dir / "evidence"
        shard_dir.mkdir(parents=True, exist_ok=True)
        for shard, records in shards.items():
            (shard_dir / f"{shard}.json").write_text(
                json.dumps(records, indent=2, sort_keys=True), encoding="utf-8"
            )
        (shard_dir / "shards.json").write_text(
            json.dumps(shard_of, indent=2, sort_keys=True), encoding="utf-8"
        )
