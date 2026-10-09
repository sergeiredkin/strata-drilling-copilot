// "Data QC per well" — comp S5-Trust.dc.html. Rig-state agreement comes from
// eval.rigstate_agreement, which the fixture generator hasn't populated yet (all null) — shown
// honestly as "—" rather than inventing a number, per CLAUDE.md's "unknown values are null + a
// visible placeholder".
import type { EvalReport } from '../../contracts/types'
import { Num } from '../../trust/Num'

export function QcTable({ report }: { report: EvalReport }) {
  const agreementByWell = new Map(report.rigstate_agreement.map((r) => [r.well, r.agreement]))

  return (
    <div className="flex flex-col gap-2.5">
      <div className="overflow-x-auto">
        <table className="w-full min-w-[620px] border-collapse text-dense">
          <thead>
            <tr className="font-condensed text-label uppercase text-text-3">
              <th className="border-b px-2.5 py-2 text-left" style={{ borderColor: 'var(--line)' }}>
                Wellbore
              </th>
              <th className="border-b px-2.5 py-2 text-left" style={{ borderColor: 'var(--line)' }}>
                Gap hours
              </th>
              <th className="border-b px-2.5 py-2 text-left" style={{ borderColor: 'var(--line)' }}>
                Spikes removed
              </th>
              <th className="border-b px-2.5 py-2 text-left" style={{ borderColor: 'var(--line)' }}>
                Unit fixes
              </th>
              <th className="border-b px-2.5 py-2 text-left" style={{ borderColor: 'var(--line)' }}>
                Sentinels removed
              </th>
              <th className="border-b px-2.5 py-2 text-left" style={{ borderColor: 'var(--line)' }}>
                Rig-state agreement vs DDR
              </th>
            </tr>
          </thead>
          <tbody>
            {report.qc.map((q) => {
              const agreement = agreementByWell.get(q.well) ?? null
              const pct = agreement?.value ?? null
              return (
                <tr key={q.well} className="font-mono">
                  <td className="border-b px-2.5 py-2" style={{ borderColor: 'var(--line-soft)' }}>
                    {q.well}
                  </td>
                  <td className="border-b px-2.5 py-2" style={{ borderColor: 'var(--line-soft)' }}>
                    <Num q={q.gap_hours} />
                  </td>
                  <td className="border-b px-2.5 py-2" style={{ borderColor: 'var(--line-soft)' }}>
                    {q.spikes_removed}
                  </td>
                  <td className="border-b px-2.5 py-2" style={{ borderColor: 'var(--line-soft)' }}>
                    {q.unit_fixes}
                  </td>
                  <td className="border-b px-2.5 py-2" style={{ borderColor: 'var(--line-soft)' }}>
                    {q.sentinels_removed}
                  </td>
                  <td className="border-b px-2.5 py-2" style={{ borderColor: 'var(--line-soft)' }}>
                    <div className="flex items-center gap-2">
                      <div className="h-2 w-[120px] rounded-full" style={{ background: 'var(--line-soft)' }}>
                        <div
                          className="h-2 rounded-full"
                          style={{ width: pct !== null ? `${pct}%` : '0%', background: 'var(--link)' }}
                        />
                      </div>
                      <span>{pct !== null ? `${pct.toFixed(0)} %` : '—'}</span>
                    </div>
                  </td>
                </tr>
              )
            })}
          </tbody>
        </table>
      </div>
      <p className="m-0 text-meta text-text-2">
        Agreement = share of DDR-booked minutes where the sensor-derived state maps to the same
        op code, after the tolerance shown in each mismatch.
      </p>
    </div>
  )
}
