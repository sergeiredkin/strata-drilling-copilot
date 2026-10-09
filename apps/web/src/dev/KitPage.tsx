// /dev/kit — dev-only showcase of every trust-kit component state (T4.4 accept criteria).
import { useWells } from '../data/hooks'
import { InsufficientData } from '../trust/InsufficientData'
import { Limitation } from '../trust/Limitation'
import { MockBadge } from '../trust/MockBadge'
import { ModeBadge } from '../trust/ModeBadge'
import { ConfidenceBadge } from '../trust/ConfidenceBadge'
import { Num } from '../trust/Num'

const LEVELS = ['high', 'medium', 'low', 'insufficient'] as const

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <section className="mb-8">
      <h2 className="mb-3 text-card-title text-text">{title}</h2>
      <div className="flex flex-wrap items-start gap-4">{children}</div>
    </section>
  )
}

export function KitPage() {
  const wells = useWells()
  const firstWell = wells.data?.wells[0]

  return (
    <div className="min-h-screen bg-bg p-6 text-text" data-theme="dark">
      <h1 className="mb-4 text-page-title">Trust kit — dev only</h1>

      <Section title="ConfidenceBadge">
        {LEVELS.map((level) => (
          <ConfidenceBadge key={level} c={{ level, reason: `Example ${level} reason text for hover/focus.` }} />
        ))}
      </Section>

      <Section title="MockBadge / ModeBadge">
        <MockBadge />
        <ModeBadge />
      </Section>

      <Section title="InsufficientData">
        <InsufficientData reason="Sample size is 0 for trip speed on this well." />
      </Section>

      <Section title="Limitation">
        <Limitation
          title="Surface torque only"
          text="MSE uses surface torque, not downhole — a stated simplification, not a hidden one."
        />
      </Section>

      <Section title="Num — real evidence (hover or Tab to it)">
        {firstWell ? (
          <Num q={firstWell.qc_score} kind="kpi" />
        ) : (
          <span className="text-text-3">loading wells.json…</span>
        )}
      </Section>

      <Section title="Num — unverified claim">
        {firstWell ? (
          <Num
            q={firstWell.qc_score}
            verified={false}
            verifyNote="evidence records a different value than claimed"
          />
        ) : (
          <span className="text-text-3">loading wells.json…</span>
        )}
      </Section>

      <Section title="Num — missing evidence record">
        <Num q={{ value: 42, unit: 'kN', evidence_id: 'ev_0000000000' }} />
      </Section>
    </div>
  )
}
