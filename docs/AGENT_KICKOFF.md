# Kick-off prompt for Claude Code (paste into VS Code)

You are the implementation agent for this repo. Read `CLAUDE.md` completely, then `docs/02_IMPLEMENTATION_PLAN.md`,
`tasks/BACKLOG.md`, and the docs they reference for the current task. Start with the first unchecked task on the
critical path (T0.1). For each task: restate its Goal and Accept criteria in 3–5 lines, implement it, run the
relevant tests (`make test`, and `make e2e` from T10.1 on), tick it in `tasks/BACKLOG.md`, and finish with a
summary starting with the task ID listing changed files and anything that needs Sergei's decision.
Do not push. Do not invent data. Do not skip acceptance criteria. Continue to the next task only after the
current one is accepted. Use the comps in `docs/design/comps/` as the visual reference for every screen.
