.PHONY: setup contracts contracts-check fixtures web api pipeline export test e2e reproduce lint typecheck

setup:
	pnpm install
	uv sync --all-packages

contracts:
	@echo "TODO (T1.1): generate TS/zod/Pydantic from contracts/schemas/strata.schema.json"

contracts-check: contracts
	@git diff --exit-code -- apps/web/src/contracts pipeline/strata_pipeline/contracts.py \
		|| (echo "Generated contracts are stale — run 'make contracts' and commit." && exit 1)

fixtures:
	@echo "TODO (T1.2): uv run python -m strata_pipeline.fixtures.generate"

web:
	cd apps/web && pnpm dev

api:
	@echo "TODO (T8.3): uv run uvicorn strata_api.main:app --reload --port 8000"

pipeline:
	@echo "TODO (Phase 2/3): ingest -> qc -> rigstate -> kpis -> export for WELL=$(WELL)"

export:
	@echo "TODO (T3.7): full export for all wells into apps/web/public/data"

test:
	cd apps/web && pnpm test
	uv run --all-packages pytest; status=$$?; [ $$status -eq 0 ] || [ $$status -eq 5 ]

lint:
	cd apps/web && pnpm lint
	uv run ruff check pipeline services eval

typecheck:
	cd apps/web && pnpm typecheck
	uv run mypy pipeline/strata_pipeline

e2e:
	cd apps/web && pnpm build && pnpm e2e

reproduce:
	@echo "TODO (T3.7): regenerate every number for WELL=$(WELL); prints manifest"
