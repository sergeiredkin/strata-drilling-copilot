// Pure "formation × type counts" matrix for S7's summary view (docs/06_SCREENS.md S7).
import type { Issue } from '../../contracts/types'

const NO_FORMATION = '— (no formation)'

export type IssueMatrix = {
  formations: string[]
  types: string[]
  counts: Record<string, Record<string, number>>
}

export function buildIssueMatrix(issues: Issue[]): IssueMatrix {
  const formations: string[] = []
  const types: string[] = []
  const counts: Record<string, Record<string, number>> = {}

  for (const issue of issues) {
    const formation = issue.formation ?? NO_FORMATION
    if (!formations.includes(formation)) formations.push(formation)
    if (!types.includes(issue.type)) types.push(issue.type)
    counts[formation] ??= {}
    counts[formation][issue.type] = (counts[formation][issue.type] ?? 0) + 1
  }

  return { formations, types, counts }
}
