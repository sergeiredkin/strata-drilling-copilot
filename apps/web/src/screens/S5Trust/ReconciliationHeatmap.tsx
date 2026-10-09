// "Sensor <-> report reconciliation · all wells" — comp S5-Trust.dc.html. Same 5-bucket
// grouping as S3's BookedVsMeasured (DDR codes vs collapsed rig states), so this heatmap and
// that per-code breakdown always agree on what counts as "the diagonal".
import type { Reconciliation, RigState } from '../../contracts/types'
import { InsufficientData } from '../../trust/InsufficientData'

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

const GROUP_LABEL: Record<Group, string> = {
  rotary: 'Rotary',
  connection: 'Conn',
  reaming: 'Ream',
  circ_flat: 'Circ/flat',
  tripping: 'Trip',
  other: 'Other',
}

/** The DDR code a row is "supposed to" match, for highlighting the diagonal — best-effort; a
 * code with no clean 1:1 rig-state analogue (CASING, CEMENT, BOP, WAIT, OTHER) gets none, so no
 * cell is ever falsely marked "agreement" for it. */
const EXPECTED_GROUP: Record<string, Group> = {
  DRILL: 'rotary',
  CIRC: 'circ_flat',
  TRIP: 'tripping',
  REAM: 'reaming',
}

function shade(pct: number, isDiagonal: boolean): { bg: string; fg: string } {
  if (isDiagonal) return { bg: 'var(--confidence-high-bg)', fg: 'var(--confidence-high-fg)' }
  if (pct >= 10) return { bg: 'var(--confidence-medium-bg)', fg: 'var(--confidence-medium-fg)' }
  if (pct > 0) return { bg: 'var(--panel-2)', fg: 'var(--text-2)' }
  return { bg: 'var(--panel)', fg: 'var(--text-3)' }
}

export function ReconciliationHeatmap({ reconciliation }: { reconciliation: Reconciliation }) {
  if (reconciliation.rows.length === 0 || reconciliation.cols.length === 0) {
    return <InsufficientData reason="No cross-well reconciliation export yet." />
  }

  const groups = (Object.keys(GROUP_LABEL) as Group[]).filter((g) =>
    reconciliation.cols.some((c) => GROUP_OF[c] === g),
  )

  const rows = reconciliation.rows.map((code, rowIdx) => {
    const cells = reconciliation.cells[rowIdx] ?? []
    const byGroup = new Map<Group, number>()
    reconciliation.cols.forEach((state, colIdx) => {
      const pct = cells[colIdx]?.pct ?? 0
      const group = GROUP_OF[state]
      byGroup.set(group, (byGroup.get(group) ?? 0) + pct)
    })
    return { code, byGroup }
  })

  return (
    <div className="flex flex-col gap-2.5">
      <p className="m-0 text-meta text-text-2">
        Rows: what the daily report booked. Columns: what the sensors measured. Cells: share of
        booked minutes. Diagonal = agreement.
      </p>
      <div className="overflow-x-auto">
        <table className="min-w-[500px] border-separate text-dense" style={{ borderSpacing: 3 }}>
          <thead>
            <tr className="font-condensed text-label uppercase text-text-3">
              <th className="px-2.5 py-2 text-left">Booked ↓ / Measured →</th>
              {groups.map((g) => (
                <th key={g} className="px-2.5 py-2 text-center">
                  {GROUP_LABEL[g]}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {rows.map((row) => (
              <tr key={row.code}>
                <td className="px-2.5 py-2 font-mono">{row.code}</td>
                {groups.map((g) => {
                  const pct = row.byGroup.get(g) ?? 0
                  const isDiagonal = EXPECTED_GROUP[row.code] === g
                  const style = shade(pct, isDiagonal)
                  return (
                    <td
                      key={g}
                      className="rounded px-2.5 py-2 text-center font-mono"
                      style={{ background: style.bg, color: style.fg }}
                    >
                      {pct.toFixed(0)} %
                    </td>
                  )
                })}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <p className="m-0 text-meta text-text-2">
        Largest off-diagonal cell is the headline: time booked as drilling that the sensors show
        as reaming, connections or flat time.
      </p>
    </div>
  )
}
