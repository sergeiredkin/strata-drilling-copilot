// "Ablation · scored against expert gold answers" — comp S5-Trust.dc.html. Accept criterion
// (docs/02_IMPLEMENTATION_PLAN.md T9.1): "no placeholder scores are shown as real numbers
// (null -> '—' with reason)" — every metric cell is null until a gold set exists, so every cell
// renders "—" and the panel says why instead of pretending there's a score.
import type { EvalReport } from '../../contracts/types'

const CONFIG_LABEL: Record<EvalReport['ablation'][number]['config'], string> = {
  no_tools: 'LLM, no tools',
  simple_rag: 'Simple RAG over reports',
  full: 'Full system',
  full_minus_physics: 'Full system − physics modules',
}

const METRIC_COLUMNS: { key: keyof EvalReport['ablation'][number]['metrics']; label: string }[] = [
  { key: 'answer_correctness', label: 'Answer correctness' },
  { key: 'numbers_verified_pct', label: 'Numbers verified' },
  { key: 'unsupported_numbers', label: 'Unsupported numbers' },
  { key: 'correct_insufficient_pct', label: 'Correct "insufficient data"' },
  { key: 'median_latency_s', label: 'Median latency' },
]

export function AblationTable({ report }: { report: EvalReport }) {
  const { gold_set: goldSet, ablation } = report

  return (
    <div className="flex flex-col gap-2.5">
      <div className="flex flex-wrap items-baseline justify-between gap-2">
        <span className="font-condensed text-label uppercase text-text-3">
          Ablation · scored against expert gold answers
        </span>
        <span className="font-mono text-meta text-text-2">
          gold set: {goldSet.n_questions} questions · version {goldSet.version} · author {goldSet.author}
        </span>
      </div>
      <div className="overflow-x-auto">
        <table className="w-full min-w-[760px] border-collapse text-dense">
          <thead>
            <tr className="font-condensed text-label uppercase text-text-3">
              <th className="border-b px-2.5 py-2 text-left" style={{ borderColor: 'var(--line)' }}>
                Configuration
              </th>
              {METRIC_COLUMNS.map((col) => (
                <th key={col.key} className="border-b px-2.5 py-2 text-left" style={{ borderColor: 'var(--line)' }}>
                  {col.label}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {ablation.map((row) => (
              <tr key={row.config} style={{ background: row.config === 'full' ? 'var(--panel-2)' : undefined }}>
                <td className="border-b px-2.5 py-2 font-semibold" style={{ borderColor: 'var(--line-soft)' }}>
                  {CONFIG_LABEL[row.config]}
                </td>
                {METRIC_COLUMNS.map((col) => (
                  <td
                    key={col.key}
                    className="border-b px-2.5 py-2 font-mono"
                    style={{ borderColor: 'var(--line-soft)', color: 'var(--text-2)' }}
                  >
                    {row.metrics[col.key] ?? '—'}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <p className="m-0 text-meta text-text-2">
        {goldSet.status === 'pending'
          ? 'Empty until the gold set exists — the page says so rather than showing placeholder scores.'
          : `Gold set status: ${goldSet.status}.`}{' '}
        Each cell will link to the per-question results in <span className="font-mono">GET /eval</span> once scored.
      </p>
    </div>
  )
}
