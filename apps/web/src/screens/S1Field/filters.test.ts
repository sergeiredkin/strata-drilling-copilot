import { describe, expect, it } from 'vitest'
import type { WellSummary } from '../../contracts/types'
import { applyFilters, DEFAULT_FILTERS, filtersToParams, paramsToFilters, type S1Filters } from './filters'

function well(overrides: Partial<WellSummary>): WellSummary {
  return {
    id: 'x',
    name: 'Test Well',
    field: 'Volve',
    years: null,
    md_range: [0, 1000],
    sections: ['8½'],
    coverage: [
      { kind: 'time_logs', status: 'full' },
      { kind: 'depth_logs', status: 'full' },
      { kind: 'daily_reports', status: 'full' },
      { kind: 'formation_tops', status: 'full' },
      { kind: 'survey', status: 'full' },
      { kind: 'mud', status: 'full' },
    ],
    qc_score: { value: 0.5, unit: '1', evidence_id: 'ev_0000000000' },
    confidence: { level: 'high', reason: '' },
    is_mock: true,
    ...overrides,
  }
}

describe('applyFilters', () => {
  const wells = [
    well({ id: 'a', name: 'Alpha', field: 'Volve', confidence: { level: 'high', reason: '' } }),
    well({ id: 'b', name: 'Beta', field: 'FORGE', confidence: { level: 'low', reason: '' } }),
    well({
      id: 'c',
      name: 'Gamma',
      field: 'Volve',
      confidence: { level: 'low', reason: '' },
      coverage: [
        { kind: 'time_logs', status: 'none' },
        { kind: 'depth_logs', status: 'full' },
        { kind: 'daily_reports', status: 'none' },
        { kind: 'formation_tops', status: 'full' },
        { kind: 'survey', status: 'full' },
        { kind: 'mud', status: 'full' },
      ],
    }),
  ]

  it('no filters returns everything', () => {
    expect(applyFilters(wells, DEFAULT_FILTERS)).toHaveLength(3)
  })

  it('search is case-insensitive substring match on name', () => {
    const result = applyFilters(wells, { ...DEFAULT_FILTERS, search: 'alph' })
    expect(result.map((w) => w.id)).toEqual(['a'])
  })

  it('field filter', () => {
    const result = applyFilters(wells, { ...DEFAULT_FILTERS, field: 'FORGE' })
    expect(result.map((w) => w.id)).toEqual(['b'])
  })

  it('needsTimeLogs excludes wells with no time_logs coverage', () => {
    const result = applyFilters(wells, { ...DEFAULT_FILTERS, needsTimeLogs: true })
    expect(result.map((w) => w.id)).toEqual(['a', 'b'])
  })

  it('needsDailyReports excludes wells with no daily_reports coverage', () => {
    const result = applyFilters(wells, { ...DEFAULT_FILTERS, needsDailyReports: true })
    expect(result.map((w) => w.id)).toEqual(['a', 'b'])
  })

  it('hideLowConfidence excludes low-confidence wells', () => {
    const result = applyFilters(wells, { ...DEFAULT_FILTERS, hideLowConfidence: true })
    expect(result.map((w) => w.id)).toEqual(['a'])
  })

  it('filters combine with AND', () => {
    const result = applyFilters(wells, { ...DEFAULT_FILTERS, field: 'Volve', hideLowConfidence: true })
    expect(result.map((w) => w.id)).toEqual(['a'])
  })

  it('a well matching no filter criteria is excluded even if some match', () => {
    const result = applyFilters(wells, { ...DEFAULT_FILTERS, field: 'Volve', needsTimeLogs: true })
    // c is Volve but has no time_logs coverage -> excluded; a is Volve with full time_logs -> kept
    expect(result.map((w) => w.id)).toEqual(['a'])
  })
})

describe('filters <-> URL params', () => {
  it('round-trips a full filter set', () => {
    const f: S1Filters = {
      search: 'f-11',
      field: 'Volve',
      needsTimeLogs: true,
      needsDailyReports: true,
      hideLowConfidence: true,
    }
    expect(paramsToFilters(filtersToParams(f))).toEqual(f)
  })

  it('default filters produce an empty param bag', () => {
    expect(filtersToParams(DEFAULT_FILTERS)).toEqual({})
  })

  it('an unknown field value falls back to "All"', () => {
    expect(paramsToFilters({ field: 'nonsense' }).field).toBe('All')
  })
})
