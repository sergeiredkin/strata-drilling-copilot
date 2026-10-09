// S1 Field overview — docs/06_SCREENS.md S1, comp docs/design/comps/S1-Field.dc.html.
import { useMemo, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import type { WellId, WellSummary } from '../../contracts/types'
import { getDataSource } from '../../data/createDataSource'
import { useWells } from '../../data/hooks'
import { useView } from '../../state/view'
import { ConfidenceBadge } from '../../trust/ConfidenceBadge'
import { MockBadge } from '../../trust/MockBadge'
import { Num } from '../../trust/Num'
import { CoverageCell } from './CoverageCell'
import { applyFilters, filtersToParams, paramsToFilters, type S1Filters } from './filters'

const COVERAGE_COLUMNS = [
  { kind: 'time_logs', label: 'Time logs' },
  { kind: 'depth_logs', label: 'Depth logs' },
  { kind: 'daily_reports', label: 'Daily rpts' },
  { kind: 'formation_tops', label: 'Fm tops' },
  { kind: 'survey', label: 'Survey' },
  { kind: 'mud', label: 'Mud' },
] as const

type SortKey = 'name' | 'qc' | 'confidence'
const CONFIDENCE_RANK: Record<string, number> = { high: 3, medium: 2, low: 1, insufficient: 0 }

function sortWells(wells: WellSummary[], key: SortKey): WellSummary[] {
  const sorted = [...wells]
  sorted.sort((a, b) => {
    if (key === 'name') return a.name.localeCompare(b.name)
    if (key === 'qc') return (b.qc_score.value ?? 0) - (a.qc_score.value ?? 0)
    return (CONFIDENCE_RANK[b.confidence.level] ?? 0) - (CONFIDENCE_RANK[a.confidence.level] ?? 0)
  })
  return sorted
}

function mdRange(range: [number, number]): string {
  const fmt = (n: number) => new Intl.NumberFormat('en-US').format(n)
  return `${fmt(range[0])} – ${fmt(range[1])}`
}

async function goToWorkspace(navigate: ReturnType<typeof useNavigate>, wellId: WellId) {
  try {
    const sections = await getDataSource().sections(wellId)
    const first = sections[0]
    if (first) {
      const t0 = first.t_start
      const t1 = Math.min(first.t_start + 24 * 3600 * 1000, first.t_end)
      navigate(`/well/${wellId}/workspace?t0=${t0}&t1=${t1}`)
      return
    }
  } catch {
    // summary-only well with no sections.json — fall through to an unwindowed deep link.
  }
  navigate(`/well/${wellId}/workspace`)
}

export function S1Field() {
  const wellsQuery = useWells()
  const navigate = useNavigate()
  const filterBag = useView((s) => s.filters)
  const setFilter = useView((s) => s.setFilter)
  const [sortKey, setSortKey] = useState<SortKey>('name')

  const filters: S1Filters = useMemo(() => paramsToFilters(filterBag), [filterBag])

  function updateFilters(patch: Partial<S1Filters>) {
    const next = { ...filters, ...patch }
    const nextParams = filtersToParams(next)
    const prevParams = filtersToParams(filters)
    const keys = new Set([...Object.keys(nextParams), ...Object.keys(prevParams)])
    for (const key of keys) {
      setFilter(key, nextParams[key] ?? null)
    }
  }

  const wells = useMemo(() => wellsQuery.data?.wells ?? [], [wellsQuery.data])
  const filtered = useMemo(() => sortWells(applyFilters(wells, filters), sortKey), [wells, filters, sortKey])

  return (
    <main className="mx-auto flex w-full max-w-[1360px] flex-col gap-6 px-6 py-8">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div className="flex flex-col gap-1.5">
          <h1 className="m-0 text-page-title font-semibold">Field overview</h1>
          <p className="m-0 text-body text-text-2">
            {wells.length} public wellbores · Volve (Equinor open data) and Utah FORGE. Gaps are shown, not filled.
          </p>
        </div>
        <MockBadge />
      </div>

      <div className="flex flex-wrap items-center gap-2.5">
        <label htmlFor="s1-search" className="font-condensed text-label uppercase text-text-3">
          Search
        </label>
        <input
          id="s1-search"
          type="search"
          placeholder="Wellbore name"
          value={filters.search}
          onChange={(e) => updateFilters({ search: e.target.value })}
          className="min-h-9 w-52 rounded border px-3 text-dense"
          style={{ background: 'var(--panel)', borderColor: 'var(--line)', color: 'var(--text)' }}
        />

        <span className="ml-3 font-condensed text-label uppercase text-text-3">Field</span>
        {(['All', 'Volve', 'FORGE'] as const).map((f) => (
          <button
            key={f}
            type="button"
            onClick={() => updateFilters({ field: f })}
            aria-pressed={filters.field === f}
            className="min-h-9 rounded border px-3.5 text-dense"
            style={{
              background: 'var(--panel)',
              borderColor: filters.field === f ? 'var(--accent)' : 'var(--line)',
              color: 'var(--text)',
            }}
          >
            {f}
          </button>
        ))}

        <span className="ml-3 font-condensed text-label uppercase text-text-3">Needs</span>
        <button
          type="button"
          onClick={() => updateFilters({ needsTimeLogs: !filters.needsTimeLogs })}
          aria-pressed={filters.needsTimeLogs}
          className="min-h-9 rounded border px-3.5 text-dense"
          style={{
            background: 'var(--panel)',
            borderColor: filters.needsTimeLogs ? 'var(--accent)' : 'var(--line)',
            color: 'var(--text)',
          }}
        >
          Time logs
        </button>
        <button
          type="button"
          onClick={() => updateFilters({ needsDailyReports: !filters.needsDailyReports })}
          aria-pressed={filters.needsDailyReports}
          className="min-h-9 rounded border px-3.5 text-dense"
          style={{
            background: 'var(--panel)',
            borderColor: filters.needsDailyReports ? 'var(--accent)' : 'var(--line)',
            color: 'var(--text)',
          }}
        >
          Daily reports
        </button>
        <button
          type="button"
          onClick={() => updateFilters({ hideLowConfidence: !filters.hideLowConfidence })}
          aria-pressed={filters.hideLowConfidence}
          className="min-h-9 rounded border px-3.5 text-dense"
          style={{
            background: 'var(--panel)',
            borderColor: filters.hideLowConfidence ? 'var(--accent)' : 'var(--line)',
            color: 'var(--text)',
          }}
        >
          Hide low confidence
        </button>
      </div>

      <div className="flex flex-wrap items-center gap-[18px] text-meta text-text-2">
        <span className="inline-flex items-center gap-1.5">
          <span className="inline-block h-[14px] w-[18px] rounded-sm" style={{ background: '#2E7D5B' }} />
          {'●'} full
        </span>
        <span className="inline-flex items-center gap-1.5">
          <span
            className="inline-block h-[14px] w-[18px] rounded-sm"
            style={{ background: 'repeating-linear-gradient(45deg, #8A6A1F 0 3px, #3A2F16 3px 6px)' }}
          />
          {'◐'} partial
        </span>
        <span className="inline-flex items-center gap-1.5">
          <span
            className="inline-block h-[14px] w-[18px] rounded-sm"
            style={{ background: 'var(--panel-2)', border: '1px solid var(--line)' }}
          />
          {'○'} none
        </span>
        <span>Hover a cell for row counts, date span and source file.</span>
      </div>

      <div className="overflow-x-auto rounded border" style={{ borderColor: 'var(--line)', background: 'var(--panel)' }}>
        <table className="w-full min-w-[1180px] border-collapse">
          <thead>
            <tr className="font-condensed">
              <SortableHeader label="Wellbore" active={sortKey === 'name'} onClick={() => setSortKey('name')} />
              <th className="th">Field</th>
              <th className="th">Years</th>
              <th className="th">MD range (m)</th>
              <th className="th">Hole sections</th>
              {COVERAGE_COLUMNS.map((c) => (
                <th key={c.kind} className="th text-center">
                  {c.label}
                </th>
              ))}
              <SortableHeader label="QC score" active={sortKey === 'qc'} onClick={() => setSortKey('qc')} />
              <SortableHeader label="Confidence" active={sortKey === 'confidence'} onClick={() => setSortKey('confidence')} />
            </tr>
          </thead>
          <tbody>
            {filtered.map((w) => (
              <tr
                key={w.id}
                className="cursor-pointer"
                onClick={() => void goToWorkspace(navigate, w.id)}
              >
                <td className="td font-mono font-medium">
                  <a
                    href={`/well/${w.id}/workspace`}
                    onClick={(e) => {
                      e.preventDefault()
                      void goToWorkspace(navigate, w.id)
                    }}
                    className="text-text no-underline hover:text-link"
                  >
                    {w.name}
                  </a>
                </td>
                <td className="td">{w.field}</td>
                <td className="td font-mono text-text-2">{w.years ?? '—'}</td>
                <td className="td font-mono">{mdRange(w.md_range)}</td>
                <td className="td font-mono text-text-2">{w.sections.join(' · ')}</td>
                {COVERAGE_COLUMNS.map((c) => {
                  const cell = w.coverage.find((cc) => cc.kind === c.kind)
                  return (
                    <td key={c.kind} className="td text-center" style={{ padding: 6 }} onClick={(e) => e.stopPropagation()}>
                      {cell && <CoverageCell cell={cell} />}
                    </td>
                  )
                })}
                <td className="td" onClick={(e) => e.stopPropagation()}>
                  <div className="flex items-center gap-2">
                    <div className="h-1.5 w-16 rounded-full" style={{ background: 'var(--line-soft)' }}>
                      <div
                        className="h-1.5 rounded-full"
                        style={{ background: 'var(--link)', width: `${Math.round((w.qc_score.value ?? 0) * 100)}%` }}
                      />
                    </div>
                    <Num q={w.qc_score} showUnit={false} />
                  </div>
                </td>
                <td className="td" onClick={(e) => e.stopPropagation()}>
                  <ConfidenceBadge c={w.confidence} />
                </td>
              </tr>
            ))}
            {filtered.length === 0 && !wellsQuery.isLoading && (
              <tr>
                <td className="td text-text-2" colSpan={13}>
                  No wells match the current filters.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>

      <div className="grid grid-cols-[repeat(auto-fit,minmax(280px,1fr))] gap-4">
        <div className="flex flex-col gap-1.5 rounded border p-[18px]" style={{ borderColor: 'var(--line)', background: 'var(--panel)' }}>
          <div className="font-condensed text-label uppercase text-text-3">How the QC score is built</div>
          <div className="text-dense leading-relaxed text-text-2">
            Coverage of the 6 data types × fraction of time-log hours without gaps × share of samples surviving
            spike/sentinel removal. Formula and per-well breakdown on the Trust page.
          </div>
        </div>
        <div className="flex flex-col gap-1.5 rounded border p-[18px]" style={{ borderColor: 'var(--line)', background: 'var(--panel)' }}>
          <div className="font-condensed text-label uppercase text-text-3">Confidence</div>
          <div className="text-dense leading-relaxed text-text-2">
            Computed by the backend from data density — the same rules the copilot uses. Low-confidence wells stay
            listed; they are never silently dropped.
          </div>
        </div>
      </div>
    </main>
  )
}

function SortableHeader({ label, active, onClick }: { label: string; active: boolean; onClick: () => void }) {
  return (
    <th className="th">
      <button
        type="button"
        onClick={onClick}
        className="bg-transparent p-0 font-condensed text-label uppercase"
        style={{ color: active ? 'var(--text)' : 'var(--text-3)' }}
      >
        {label} {active ? '↓' : ''}
      </button>
    </th>
  )
}
