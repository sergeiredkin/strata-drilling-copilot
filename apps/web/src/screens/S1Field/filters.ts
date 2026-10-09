// Pure filter logic for S1 — docs/06_SCREENS.md S1: "filters combine (AND); low-confidence rows
// remain visible unless the toggle is on." Kept framework-free so it's trivially unit-testable.
import type { WellSummary } from '../../contracts/types'

export type FieldFilter = 'All' | 'Volve' | 'FORGE'

export type S1Filters = {
  search: string
  field: FieldFilter
  needsTimeLogs: boolean
  needsDailyReports: boolean
  hideLowConfidence: boolean
}

export const DEFAULT_FILTERS: S1Filters = {
  search: '',
  field: 'All',
  needsTimeLogs: false,
  needsDailyReports: false,
  hideLowConfidence: false,
}

function coverageStatus(well: WellSummary, kind: string): string | undefined {
  return well.coverage.find((c) => c.kind === kind)?.status
}

export function applyFilters(wells: WellSummary[], f: S1Filters): WellSummary[] {
  const needle = f.search.trim().toLowerCase()
  return wells.filter((w) => {
    if (needle && !w.name.toLowerCase().includes(needle)) return false
    if (f.field !== 'All' && w.field !== f.field) return false
    if (f.needsTimeLogs && coverageStatus(w, 'time_logs') === 'none') return false
    if (f.needsDailyReports && coverageStatus(w, 'daily_reports') === 'none') return false
    if (f.hideLowConfidence && w.confidence.level === 'low') return false
    return true
  })
}

/** S1 filters <-> the view store's generic `filters` query-param bag (docs/03_ARCHITECTURE.md
 * §3.2) — booleans are "1"/absent so the URL stays short, e.g. `?field=Volve&needs_time_logs=1`. */
export function filtersToParams(f: S1Filters): Record<string, string> {
  const params: Record<string, string> = {}
  if (f.search) params.q = f.search
  if (f.field !== 'All') params.field = f.field
  if (f.needsTimeLogs) params.needs_time_logs = '1'
  if (f.needsDailyReports) params.needs_daily_reports = '1'
  if (f.hideLowConfidence) params.hide_low_confidence = '1'
  return params
}

export function paramsToFilters(params: Record<string, string>): S1Filters {
  const field = params.field
  return {
    search: params.q ?? '',
    field: field === 'Volve' || field === 'FORGE' ? field : 'All',
    needsTimeLogs: params.needs_time_logs === '1',
    needsDailyReports: params.needs_daily_reports === '1',
    hideLowConfidence: params.hide_low_confidence === '1',
  }
}
