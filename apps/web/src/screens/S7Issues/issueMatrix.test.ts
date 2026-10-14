import { describe, expect, it } from 'vitest'
import type { Issue } from '../../contracts/types'
import { buildIssueMatrix } from './issueMatrix'

function issue(partial: Partial<Issue>): Issue {
  return {
    id: 'i1', well: 'W1', type: 'tight_hole', t0: 0, t1: null, md: null, formation: null,
    section: null, duration: null, mud: null, ddr_activity_ids: [], excerpt: '', report_date: '2020-01-01',
    extraction: 'rule', ...partial,
  }
}

describe('buildIssueMatrix', () => {
  it('counts issues per formation and type', () => {
    const matrix = buildIssueMatrix([
      issue({ formation: 'Hugin Fm.', type: 'tight_hole' }),
      issue({ formation: 'Hugin Fm.', type: 'tight_hole' }),
      issue({ formation: 'Hugin Fm.', type: 'losses' }),
      issue({ formation: 'Draupne Fm.', type: 'losses' }),
    ])
    expect(matrix.counts['Hugin Fm.']?.tight_hole).toBe(2)
    expect(matrix.counts['Hugin Fm.']?.losses).toBe(1)
    expect(matrix.counts['Draupne Fm.']?.losses).toBe(1)
  })

  it('buckets issues with no formation under a labelled placeholder, not dropped', () => {
    const matrix = buildIssueMatrix([issue({ formation: null, type: 'kick' })])
    expect(matrix.formations).toContain('— (no formation)')
    expect(matrix.counts['— (no formation)']?.kick).toBe(1)
  })

  it('returns empty lists for no issues', () => {
    expect(buildIssueMatrix([])).toEqual({ formations: [], types: [], counts: {} })
  })

  it('lists formations/types in first-seen order', () => {
    const matrix = buildIssueMatrix([
      issue({ formation: 'B', type: 'losses' }),
      issue({ formation: 'A', type: 'kick' }),
    ])
    expect(matrix.formations).toEqual(['B', 'A'])
    expect(matrix.types).toEqual(['losses', 'kick'])
  })
})
