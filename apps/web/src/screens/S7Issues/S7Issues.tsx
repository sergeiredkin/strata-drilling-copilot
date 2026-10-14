// S7 Issue catalogue — docs/06_SCREENS.md S7, no comp yet (built from S1's table/filter
// patterns). `/issues?well&type&formation` filters map directly onto the view store's generic
// filter bag and onto IssueQuery, so there's no separate client-side filter function the way
// S1's does — StaticSource/HttpSource already filter server/fixture-side on exactly these
// fields.
import { useMemo, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import type { Issue } from '../../contracts/types'
import { useIssues, useWells } from '../../data/hooks'
import { useView } from '../../state/view'
import { MockBadge } from '../../trust/MockBadge'
import { Num } from '../../trust/Num'
import { buildIssueMatrix } from './issueMatrix'

const TYPE_LABEL: Record<string, string> = {
  stuck_pipe: 'Stuck pipe', losses: 'Losses', tight_hole: 'Tight hole', kick: 'Kick',
  pack_off: 'Pack off', washout: 'Washout', other: 'Other',
}

function fmtDateTime(ms: number): string {
  return new Date(ms).toISOString().slice(0, 16).replace('T', ' ')
}

function IssueRow({
  issue,
  wellName,
  onOpenWorkspace,
  onOpenFormation,
}: {
  issue: Issue
  wellName: string
  onOpenWorkspace: (issue: Issue) => void
  onOpenFormation: (issue: Issue) => void
}) {
  const [expanded, setExpanded] = useState(false)
  return (
    <>
      <tr className="font-mono text-dense">
        <td className="border-b px-2 py-2 font-sans" style={{ borderColor: 'var(--line-soft)' }}>
          {TYPE_LABEL[issue.type] ?? issue.type}
        </td>
        <td className="border-b px-2 py-2 font-sans" style={{ borderColor: 'var(--line-soft)' }}>{wellName}</td>
        <td className="border-b px-2 py-2" style={{ borderColor: 'var(--line-soft)' }}>{fmtDateTime(issue.t0)}</td>
        <td className="border-b px-2 py-2" style={{ borderColor: 'var(--line-soft)' }}>{issue.md ?? '—'}</td>
        <td className="border-b px-2 py-2 font-sans" style={{ borderColor: 'var(--line-soft)' }}>
          {issue.formation ?? '—'}
        </td>
        <td className="border-b px-2 py-2 font-sans" style={{ borderColor: 'var(--line-soft)' }}>
          {issue.section ?? '—'}
        </td>
        <td className="border-b px-2 py-2" style={{ borderColor: 'var(--line-soft)' }}>
          {issue.duration ? <Num q={issue.duration} /> : '—'}
        </td>
        <td className="border-b px-2 py-2 font-sans" style={{ borderColor: 'var(--line-soft)' }}>
          {issue.mud ? (
            <>
              <Num q={issue.mud.mw} /> / <Num q={issue.mud.ecd} />
            </>
          ) : (
            '—'
          )}
        </td>
        <td className="border-b px-2 py-2" style={{ borderColor: 'var(--line-soft)' }}>{issue.extraction ?? '—'}</td>
        <td className="border-b px-2 py-2 font-sans" style={{ borderColor: 'var(--line-soft)' }}>
          <div className="flex flex-wrap gap-1.5">
            <button
              type="button"
              onClick={() => setExpanded((e) => !e)}
              aria-expanded={expanded}
              className="min-h-7 rounded border px-2 text-meta"
              style={{ borderColor: 'var(--line)', background: 'var(--panel-2)' }}
            >
              {expanded ? 'Hide excerpt' : 'Excerpt'}
            </button>
            <button
              type="button"
              onClick={() => onOpenWorkspace(issue)}
              className="min-h-7 rounded border px-2 text-meta"
              style={{ borderColor: 'var(--line)', background: 'var(--panel-2)' }}
            >
              Open in Workspace
            </button>
            <button
              type="button"
              onClick={() => onOpenFormation(issue)}
              className="min-h-7 rounded border px-2 text-meta"
              style={{ borderColor: 'var(--line)', background: 'var(--panel-2)' }}
            >
              Open in Formation
            </button>
          </div>
        </td>
      </tr>
      {expanded && (
        <tr>
          <td colSpan={10} className="border-b px-2 pb-3" style={{ borderColor: 'var(--line-soft)' }}>
            <blockquote
              className="m-0 border-l-2 pl-2.5 text-dense italic"
              style={{ borderColor: 'var(--line)', color: 'var(--text-2)' }}
            >
              &ldquo;{issue.excerpt}&rdquo;
              <span className="mt-1 block font-mono text-meta not-italic text-text-3">DDR {issue.report_date}</span>
            </blockquote>
          </td>
        </tr>
      )}
    </>
  )
}

export function S7Issues() {
  const navigate = useNavigate()
  const wells = useWells()
  const filterBag = useView((s) => s.filters)
  const setFilter = useView((s) => s.setFilter)

  const well = filterBag.well ?? undefined
  const type = filterBag.type ?? undefined
  const formation = filterBag.formation ?? undefined
  const issuesQuery = useIssues({ well, type, formation })

  const wellNameById = useMemo(
    () => new Map((wells.data?.wells ?? []).map((w) => [w.id, w.name])),
    [wells.data],
  )
  const matrix = useMemo(() => buildIssueMatrix(issuesQuery.data ?? []), [issuesQuery.data])
  const presentTypes = useMemo(
    () => [...new Set((issuesQuery.data ?? []).map((i) => i.type))],
    [issuesQuery.data],
  )

  function openWorkspace(issue: Issue) {
    const t1 = issue.t1 ?? issue.t0 + 600_000
    navigate(`/well/${issue.well}/workspace?t0=${issue.t0}&t1=${t1}`)
  }

  function openFormation(issue: Issue) {
    navigate(`/well/${issue.well}/formation`)
  }

  const anyMock = (wells.data?.wells ?? []).some((w) => w.is_mock)

  return (
    <main className="mx-auto flex w-full max-w-[1360px] flex-col gap-5 px-6 py-6">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div className="flex flex-col gap-1">
          <h1 className="m-0 text-page-title font-semibold">Issue catalogue</h1>
          <p className="m-0 text-body text-text-2">
            DDR-extracted events (rule lexicon, T12.1) — no risk score, inspection only.
          </p>
        </div>
        {anyMock && <MockBadge />}
      </div>

      <div className="flex flex-wrap items-center gap-2.5">
        <label className="flex items-center gap-1.5 text-dense">
          Well
          <select
            value={well ?? ''}
            onChange={(e) => setFilter('well', e.target.value || null)}
            className="min-h-9 rounded border px-2"
            style={{ borderColor: 'var(--line)', background: 'var(--panel)' }}
          >
            <option value="">All</option>
            {(wells.data?.wells ?? []).map((w) => (
              <option key={w.id} value={w.id}>
                {w.name}
              </option>
            ))}
          </select>
        </label>
        <label className="flex items-center gap-1.5 text-dense">
          Type
          <select
            value={type ?? ''}
            onChange={(e) => setFilter('type', e.target.value || null)}
            className="min-h-9 rounded border px-2"
            style={{ borderColor: 'var(--line)', background: 'var(--panel)' }}
          >
            <option value="">All</option>
            {presentTypes.map((t) => (
              <option key={t} value={t}>
                {TYPE_LABEL[t] ?? t}
              </option>
            ))}
          </select>
        </label>
      </div>

      {issuesQuery.isLoading ? (
        <div className="p-6 text-text-2">Loading…</div>
      ) : (issuesQuery.data ?? []).length === 0 ? (
        <p className="m-0 text-body text-text-2">
          No issues match these filters — either none were extracted for this scope yet, or the
          rule lexicon (T12.1) found nothing here.
        </p>
      ) : (
        <>
          <section
            className="overflow-x-auto rounded border"
            style={{ borderColor: 'var(--line)', background: 'var(--panel)' }}
          >
            <table className="w-full min-w-[960px] border-collapse text-dense">
              <thead>
                <tr className="font-condensed text-left text-label uppercase text-text-3">
                  <th className="border-b px-2 py-2" style={{ borderColor: 'var(--line)' }}>Type</th>
                  <th className="border-b px-2 py-2" style={{ borderColor: 'var(--line)' }}>Well</th>
                  <th className="border-b px-2 py-2" style={{ borderColor: 'var(--line)' }}>Date</th>
                  <th className="border-b px-2 py-2" style={{ borderColor: 'var(--line)' }}>MD</th>
                  <th className="border-b px-2 py-2" style={{ borderColor: 'var(--line)' }}>Formation</th>
                  <th className="border-b px-2 py-2" style={{ borderColor: 'var(--line)' }}>Section</th>
                  <th className="border-b px-2 py-2" style={{ borderColor: 'var(--line)' }}>Duration</th>
                  <th className="border-b px-2 py-2" style={{ borderColor: 'var(--line)' }}>MW / ECD</th>
                  <th className="border-b px-2 py-2" style={{ borderColor: 'var(--line)' }}>Extraction</th>
                  <th className="border-b px-2 py-2" style={{ borderColor: 'var(--line)' }}>Actions</th>
                </tr>
              </thead>
              <tbody>
                {(issuesQuery.data ?? []).map((issue) => (
                  <IssueRow
                    key={issue.id}
                    issue={issue}
                    wellName={wellNameById.get(issue.well) ?? issue.well}
                    onOpenWorkspace={openWorkspace}
                    onOpenFormation={openFormation}
                  />
                ))}
              </tbody>
            </table>
          </section>

          <section
            className="flex flex-col gap-2.5 overflow-x-auto rounded border p-4"
            style={{ borderColor: 'var(--line)', background: 'var(--panel)' }}
          >
            <span className="font-condensed text-label uppercase text-text-3">Formation × type counts</span>
            <table className="border-collapse text-dense">
              <thead>
                <tr className="font-condensed text-left text-label uppercase text-text-3">
                  <th className="border-b px-2 py-1.5" style={{ borderColor: 'var(--line)' }}>Formation</th>
                  {matrix.types.map((t) => (
                    <th key={t} className="border-b px-2 py-1.5 text-right" style={{ borderColor: 'var(--line)' }}>
                      {TYPE_LABEL[t] ?? t}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {matrix.formations.map((f) => (
                  <tr key={f} className="font-mono">
                    <td className="border-b px-2 py-1.5 font-sans" style={{ borderColor: 'var(--line-soft)' }}>
                      {f}
                    </td>
                    {matrix.types.map((t) => (
                      <td
                        key={t}
                        className="border-b px-2 py-1.5 text-right"
                        style={{ borderColor: 'var(--line-soft)' }}
                      >
                        {matrix.counts[f]?.[t] ?? 0}
                      </td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </section>
        </>
      )}
    </main>
  )
}
