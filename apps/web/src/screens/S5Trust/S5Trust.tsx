// S5 Trust — evaluation and limits. docs/06_SCREENS.md S5, comp S5-Trust.dc.html.
import { useEvalReport, useModelCard, useReconciliation, useRepro } from '../../data/hooks'
import { InsufficientData } from '../../trust/InsufficientData'
import { Limitation } from '../../trust/Limitation'
import { MockBadge } from '../../trust/MockBadge'
import { AblationTable } from './AblationTable'
import { QcTable } from './QcTable'
import { ReconciliationHeatmap } from './ReconciliationHeatmap'

const LIMITATIONS = [
  {
    title: 'Surface data only.',
    text: 'No downhole sensors; anything downhole is inferred.',
  },
  {
    title: '1 Hz sampling.',
    text: 'High-frequency vibration (stick-slip, whirl) is not visible.',
  },
  {
    title: 'Geothermal vs hydrocarbon.',
    text: 'FORGE granite wells and Volve sandstone wells are not like-for-like benchmarks.',
  },
  {
    title: 'Daily reports are coarse.',
    text: '15–30 min rows; some mismatches are granularity, not error.',
  },
  {
    title: 'Advisory only.',
    text: 'No setpoints, no control, no fleet-scale claims.',
  },
  {
    title: 'Licences.',
    text: 'Volve data released by Equinor under the Equinor Open Data Licence; Utah FORGE data released under U.S. DOE public-data terms. Both demo datasets only, not a vendor product.',
  },
]

const POSITIONING_INDUSTRY = [
  {
    capability: 'Invisible lost time',
    industry: 'Headline % quoted; baseline and method not defined.',
    strata: 'Defined composite best, per-category result, one-command reproduction.',
  },
  {
    capability: 'Daily-report integration',
    industry: 'Reports merged into dashboards; disagreement not reported.',
    strata: 'Booked-vs-measured matrix with tolerance and agreement per well.',
  },
  {
    capability: 'Formation / hazard ML',
    industry: 'Tree ensembles; validation scheme and metrics not in abstract.',
    strata: 'Leave-one-well-out, calibrated, baseline-compared, abstains; events shown as precursors, not scores.',
  },
  {
    capability: 'Parameter recommendations',
    industry: 'WOB / RPM / mud-weight recommendation engine.',
    strata: 'Out of scope by design: advisory analytics only.',
  },
  {
    capability: 'AI answers',
    industry: 'Not covered.',
    strata: 'Tool-grounded copilot, per-number verifier, ablation against gold answers.',
  },
]

function ModelCardPanel({ model, title, seeOn }: { model: 'formation' | 'events'; title: string; seeOn?: string }) {
  const card = useModelCard(model)

  return (
    <div className="flex flex-col gap-1.5 rounded p-3.5" style={{ background: 'var(--bg)' }}>
      <div className="flex flex-wrap items-baseline justify-between gap-2">
        <span className="text-body font-semibold text-text">{title}</span>
        {seeOn && (
          <a href={seeOn} className="text-meta text-link">
            See on S6 →
          </a>
        )}
      </div>
      {card.data ? (
        <pre className="m-0 whitespace-pre-wrap font-mono text-label leading-relaxed text-text-2">
          {`validation   ${card.data.validation}\nwells        ${card.data.n_wells ?? '—'}\nmetrics      ${Object.entries(
            card.data.metrics,
          )
            .map(([k, v]) => `${k}=${v?.value ?? '—'}`)
            .join(', ')}`}
        </pre>
      ) : (
        <p className="m-0 text-label text-text-2">
          No {model} model card export yet — this PR-3/4 scope hasn&apos;t landed.
        </p>
      )}
    </div>
  )
}

export function S5Trust() {
  const evalReport = useEvalReport()
  const reconciliation = useReconciliation()
  const repro = useRepro()

  if (evalReport.isLoading) {
    return <div className="p-6 text-text-2">Loading…</div>
  }
  if (!evalReport.data) {
    return (
      <main className="mx-auto max-w-[1360px] p-6">
        <InsufficientData reason="No evaluation export yet." />
      </main>
    )
  }

  return (
    <main className="mx-auto flex w-full max-w-[1360px] flex-col gap-[22px] px-6 py-7">
      <div className="flex flex-col gap-1.5">
        <h1 className="m-0 text-page-title font-semibold">Trust — evaluation and limits</h1>
        <p className="m-0 max-w-[820px] text-body leading-relaxed text-text-2">
          What was cleaned, how well the rig-state classifier agrees with the daily reports, how
          much each part of the system contributes, and what this demo cannot see.
        </p>
      </div>

      <div className="flex flex-wrap gap-4">
        <section
          className="flex min-w-0 flex-[3_1_600px] flex-col gap-3 rounded border p-4.5"
          style={{ borderColor: 'var(--line)', background: 'var(--panel)' }}
        >
          <div className="flex flex-wrap items-center justify-between gap-2">
            <span className="font-condensed text-label uppercase text-text-3">Data QC per well</span>
            <MockBadge />
          </div>
          <QcTable report={evalReport.data} />
        </section>

        <section
          className="flex min-w-0 flex-[2_1_380px] flex-col gap-3 rounded border p-4.5"
          style={{ borderColor: 'var(--line)', background: 'var(--panel)' }}
        >
          <span className="font-condensed text-label uppercase text-text-3">Known limitations</span>
          <div className="flex flex-col gap-2">
            {LIMITATIONS.map((l) => (
              <Limitation key={l.title} title={l.title} text={l.text} />
            ))}
          </div>
        </section>
      </div>

      <section className="rounded border p-4.5" style={{ borderColor: 'var(--line)', background: 'var(--panel)' }}>
        <AblationTable report={evalReport.data} />
      </section>

      <div className="flex flex-wrap gap-4">
        <section
          className="flex min-w-0 flex-[3_1_600px] flex-col gap-3 rounded border p-4.5"
          style={{ borderColor: 'var(--line)', background: 'var(--panel)' }}
        >
          <span className="font-condensed text-label uppercase text-text-3">
            Sensor ↔ report reconciliation · all wells
          </span>
          {reconciliation.data ? (
            <ReconciliationHeatmap reconciliation={reconciliation.data} />
          ) : (
            <InsufficientData reason="Loading…" />
          )}
        </section>

        <section
          className="flex min-w-0 flex-[2_1_400px] flex-col gap-3 rounded border p-4.5"
          style={{ borderColor: 'var(--line)', background: 'var(--panel)' }}
        >
          <span className="font-condensed text-label uppercase text-text-3">Model cards</span>
          <ModelCardPanel model="formation" title="Formation classifier" seeOn="/well/15_9-F-11_A/formation" />
          <ModelCardPanel model="events" title="Event retrieval (not a predictor)" />
        </section>
      </div>

      <section className="rounded border p-4.5" style={{ borderColor: 'var(--line)', background: 'var(--panel)' }}>
        <span className="font-condensed text-label uppercase text-text-3">
          Positioning versus standard industry practice
        </span>
        <div className="mt-2.5 overflow-x-auto">
          <table className="w-full min-w-[820px] border-collapse text-dense">
            <thead>
              <tr className="font-condensed text-label uppercase text-text-3">
                <th className="border-b px-2.5 py-2 text-left" style={{ borderColor: 'var(--line)', width: '22%' }}>
                  Capability
                </th>
                <th className="border-b px-2.5 py-2 text-left" style={{ borderColor: 'var(--line)', width: '39%' }}>
                  Typical published practice
                </th>
                <th className="border-b px-2.5 py-2 text-left" style={{ borderColor: 'var(--line)' }}>
                  What STRATA shows
                </th>
              </tr>
            </thead>
            <tbody>
              {POSITIONING_INDUSTRY.map((p) => (
                <tr key={p.capability}>
                  <td
                    className="border-b px-2.5 py-2.5 align-top font-semibold"
                    style={{ borderColor: 'var(--line-soft)' }}
                  >
                    {p.capability}
                  </td>
                  <td
                    className="border-b px-2.5 py-2.5 align-top text-text-2"
                    style={{ borderColor: 'var(--line-soft)' }}
                  >
                    {p.industry}
                  </td>
                  <td className="border-b px-2.5 py-2.5 align-top" style={{ borderColor: 'var(--line-soft)' }}>
                    {p.strata}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <p className="m-0 mt-2.5 text-meta text-text-3">
          References: SPE-227235-MS (MEOS GEO 2025), SPE-229231-MS (ADIPEC 2025). Comparison is
          with what those abstracts report, not with any vendor product.
        </p>
      </section>

      <section className="rounded border p-4.5" style={{ borderColor: 'var(--line)', background: 'var(--panel)' }}>
        <span className="font-condensed text-label uppercase text-text-3">Positioning versus the TADI paper</span>
        <div className="mt-2.5 grid grid-cols-[repeat(auto-fit,minmax(300px,1fr))] gap-3.5">
          <div className="flex flex-col gap-1.5 rounded p-3.5" style={{ background: 'var(--bg)' }}>
            <span className="text-body font-semibold text-text">TADI — what it does</span>
            <p className="m-0 text-dense leading-relaxed text-text-2">
              Lu, &quot;TADI: Tool-Augmented Drilling Intelligence via Agentic LLM Orchestration
              over Heterogeneous Wellsite Data&quot; (arXiv:2605.00060v1, 2026) — a single-author,
              framework-free agentic system over the same public Volve dataset. An LLM
              orchestrates 12 domain tools across a dual DuckDB/ChromaDB store (1,759 daily
              reports, WITSML records, formation tops) to answer a 130-question stress-test
              taxonomy, scored by the paper&apos;s own Evidence Grounding Score (EGS) — a proxy
              based on measurements cited, DDR quotations attributed, and required answer
              sections present. It is a research prototype: no UI, no stated per-number verifier
              against live tool output, and no gap/confidence treatment in the answers.
            </p>
          </div>
          <div className="flex flex-col gap-1.5 rounded p-3.5" style={{ background: 'var(--bg)' }}>
            <span className="text-body font-semibold text-text">What STRATA adds</span>
            <ul className="m-0 flex flex-col gap-1 pl-[18px] text-dense leading-relaxed text-text">
              <li>Per-number verifier against tool outputs</li>
              <li>Data gaps and confidence shown in the UI</li>
              <li>Ablations published alongside results</li>
              <li>Built only on open public data, reproducible from a clone</li>
            </ul>
          </div>
        </div>
      </section>

      <section className="rounded border p-4.5" style={{ borderColor: 'var(--line)', background: 'var(--panel)' }}>
        <span className="font-condensed text-label uppercase text-text-3">Reproduce this export</span>
        {repro.data ? (
          <pre className="m-0 mt-2.5 whitespace-pre-wrap font-mono text-label leading-relaxed text-text">
            {`commit   ${repro.data.git_commit ? repro.data.git_commit.slice(0, 12) : 'unknown'}\ndata     ${repro.data.data_files.length} files · sha256 manifest\ncommand  ${repro.data.command}`}
          </pre>
        ) : (
          <p className="m-0 mt-2.5 text-dense text-text-2">No repro manifest exported yet.</p>
        )}
      </section>
    </main>
  )
}
