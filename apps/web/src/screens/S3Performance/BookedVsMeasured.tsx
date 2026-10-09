// Booked vs measured — what the DDR says vs what the sensors show, comp S3-Performance.dc.html.
// Reconciliation gives, per DDR code, the % of its booked minutes that sensors classify into
// each rig state; segments are grouped into the comp's 5 legend buckets.
import type { Reconciliation, RigState } from '../../contracts/types'
import { Num } from '../../trust/Num'

type Group = 'rotary' | 'connection' | 'reaming' | 'circ_flat' | 'tripping' | 'other'

const GROUP_OF: Record<RigState, Group> = {
  rotary_drilling: 'rotary',
  sliding: 'rotary',
  connection: 'connection',
  trip_in: 'tripping',
  trip_out: 'tripping',
  reaming: 'reaming',
  circulating: 'circ_flat',
  out_of_hole: 'other',
  unknown: 'other',
}

const GROUP_STYLE: Record<Group, { label: string; bg: string; fg: string }> = {
  rotary: { label: 'Rotary', bg: '#1F64AA', fg: '#FFFFFF' },
  connection: { label: 'Connection', bg: '#E39A1E', fg: '#0A0E13' },
  reaming: {
    label: 'Reaming',
    bg: 'repeating-linear-gradient(90deg,#4FD1AE 0 3px,#2A9C7E 3px 6px)',
    fg: '#0A0E13',
  },
  circ_flat: { label: 'Circulating / flat', bg: '#5E7387', fg: '#FFFFFF' },
  tripping: { label: 'Tripping', bg: '#9670E0', fg: '#0A0E13' },
  other: { label: 'Other', bg: '#2B3542', fg: '#A9B6C3' },
}

const LABEL_MIN_PCT = 8

function agreementColor(pct: number): string {
  if (pct >= 80) return '#6FF0B4'
  if (pct >= 60) return '#FFC861'
  return '#FF9A7A'
}

export function BookedVsMeasured({
  reconciliation,
  wellId,
}: {
  reconciliation: Reconciliation
  wellId: string
}) {
  const rows = reconciliation.rows.map((code, rowIdx) => {
    const cells = reconciliation.cells[rowIdx] ?? []
    const byGroup = new Map<Group, number>()
    for (let colIdx = 0; colIdx < reconciliation.cols.length; colIdx++) {
      const state = reconciliation.cols[colIdx]
      const cell = cells[colIdx]
      if (!state || !cell) continue
      const group = GROUP_OF[state]
      byGroup.set(group, (byGroup.get(group) ?? 0) + cell.pct)
    }
    const agreement = reconciliation.agreement.find((a) => a.code === code)
    return { code, byGroup, agreement }
  })

  const groupsPresent = [
    ...new Set(rows.flatMap((r) => [...r.byGroup.keys()])),
  ].sort((a, b) => Object.keys(GROUP_STYLE).indexOf(a) - Object.keys(GROUP_STYLE).indexOf(b))

  return (
    <section
      className="flex min-w-0 flex-[3_1_600px] flex-col gap-3.5 rounded border p-4.5"
      style={{ borderColor: 'var(--line)', background: 'var(--panel)' }}
    >
      <span className="font-condensed text-label uppercase text-text-3">
        Booked vs measured · what the daily report says vs what the sensors show
      </span>
      <div className="flex flex-col gap-2.5">
        {rows.map((row) => (
          <div key={row.code} className="flex flex-wrap items-center gap-2.5">
            <div className="flex w-[150px] flex-none flex-col">
              <span className="font-mono text-dense">{row.code}</span>
              <span className="text-meta text-text-2">
                booked{' '}
                {row.agreement?.booked ? <Num q={row.agreement.booked} /> : '—'}
              </span>
            </div>
            <a
              href={`/well/${wellId}/workspace`}
              aria-label={`Open ${row.code} intervals in Workspace`}
              className="flex h-[26px] flex-1 overflow-hidden rounded"
              style={{ minWidth: 280 }}
            >
              {[...row.byGroup.entries()].map(([group, pct]) => {
                const style = GROUP_STYLE[group]
                return (
                  <span
                    key={group}
                    className="flex items-center justify-center overflow-hidden whitespace-nowrap font-mono text-meta"
                    style={{ width: `${pct}%`, background: style.bg, color: style.fg }}
                  >
                    {pct >= LABEL_MIN_PCT ? `${style.label} ${pct.toFixed(0)}%` : ''}
                  </span>
                )
              })}
            </a>
            <div
              className="w-[120px] flex-none text-right font-mono text-meta"
              style={{ color: row.agreement ? agreementColor(row.agreement.pct.value ?? 0) : 'var(--text-2)' }}
            >
              {row.agreement ? <Num q={row.agreement.pct} /> : '—'} agree
            </div>
          </div>
        ))}
      </div>
      <div className="flex flex-wrap gap-4 text-meta text-text-2">
        {groupsPresent.map((group) => {
          const style = GROUP_STYLE[group]
          return (
            <span key={group} className="inline-flex items-center gap-1.5">
              <span className="inline-block h-2.5 w-4" style={{ background: style.bg }} />
              {style.label}
            </span>
          )
        })}
        <span>
          Tolerance: ±{reconciliation.tolerance.boundary_slack_min} min at row boundaries, minimum
          interval {reconciliation.tolerance.min_duration_min} min.
        </span>
      </div>
    </section>
  )
}
