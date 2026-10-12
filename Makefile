.PHONY: setup contracts contracts-check fixtures web api pipeline export test e2e reproduce lint typecheck

setup:
	pnpm install
	uv sync --all-packages

contracts:
	node contracts/codegen/gen_ts.mjs
	node contracts/codegen/gen_zod.mjs
	bash contracts/codegen/gen_py.sh

contracts-check: contracts
	@git diff --exit-code -- apps/web/src/contracts pipeline/strata_pipeline/contracts.py \
		|| (echo "Generated contracts are stale — run 'make contracts' and commit." && exit 1)

fixtures:
	uv run --project pipeline python3 -m strata_pipeline.fixtures.generate

web:
	cd apps/web && pnpm dev

api:
	uv run --project services/api uvicorn strata_api.main:app --reload --port 8000

pipeline:
	uv run --project pipeline python3 -m strata_pipeline.export.cli_pipeline --well $(WELL)

export:
	uv run --project pipeline python3 -m strata_pipeline.export.cli_export

test:
	cd apps/web && pnpm test
	uv run --all-packages pytest; status=$$?; [ $$status -eq 0 ] || [ $$status -eq 5 ]

lint:
	cd apps/web && pnpm lint && pnpm copy-lint
	uv run ruff check pipeline services eval

typecheck:
	cd apps/web && pnpm typecheck
	uv run mypy pipeline/strata_pipeline

e2e:
	cd apps/web && pnpm build && pnpm e2e

reproduce:
	uv run --project pipeline python3 -m strata_pipeline.export.cli_reproduce --well $(WELL)
