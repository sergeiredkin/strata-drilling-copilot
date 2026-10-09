// docs/05_DESIGN_SYSTEM.md §6: tool, params (mono), sources (file, sha256 short, channels,
// window), value SI + converted, link "Show this window in the workspace". Pure content —
// Num.tsx owns the floating positioning/interactions and renders this inside the floating panel.
import type { EvidenceId } from '../contracts/types'
import { useEvidence } from '../data/hooks'
import { usePrefs } from '../state/prefs'
import { convertValue } from '../units/registry'

export type EvidencePopoverProps = {
  id: EvidenceId
  /** Set when the caller is a Claim (copilot answer) whose own verification failed — shows the
   * "✕ not verified" line even though the underlying Evidence record itself is always real. */
  verified?: boolean
  verifyNote?: string
}

function shortSha(sha256: string): string {
  return sha256.length > 10 ? `${sha256.slice(0, 10)}…` : sha256
}

export function EvidencePopover({ id, verified, verifyNote }: EvidencePopoverProps) {
  const { data: evidence, isLoading, isError } = useEvidence(id)
  const units = usePrefs((s) => s.units)

  if (isLoading) {
    return (
      <div className="w-72 p-3 text-dense" style={{ color: 'var(--text-2)' }}>
        Loading evidence…
      </div>
    )
  }

  if (isError || !evidence) {
    return (
      <div className="w-72 p-3 text-dense" style={{ color: 'var(--danger)' }}>
        No evidence record for {id}.
      </div>
    )
  }

  const converted = convertValue(evidence.value, evidence.unit, units === 'oilfield' ? 'oilfield' : 'metric')
  const other = convertValue(evidence.value, evidence.unit, units === 'oilfield' ? 'metric' : 'oilfield')

  return (
    <div className="w-80 p-3 text-dense" style={{ color: 'var(--text)' }}>
      {verified === false && (
        <div
          className="mb-2 rounded px-2 py-1 text-label font-semibold"
          style={{ background: 'color-mix(in srgb, var(--danger) 18%, transparent)', color: 'var(--danger)' }}
        >
          {'✕'} not verified{verifyNote ? ` — ${verifyNote}` : ''}
        </div>
      )}
      <dl className="m-0 grid grid-cols-[auto_1fr] gap-x-2 gap-y-1">
        <dt className="text-label uppercase text-text-3">Tool</dt>
        <dd className="m-0 font-mono text-label">{evidence.tool}</dd>

        <dt className="text-label uppercase text-text-3">Params</dt>
        <dd className="m-0 whitespace-pre-wrap font-mono text-label">{JSON.stringify(evidence.params)}</dd>

        <dt className="text-label uppercase text-text-3">Value</dt>
        <dd className="m-0 font-mono text-label">
          {evidence.value ?? '—'} {evidence.unit}
          {evidence.value !== null && (
            <span style={{ color: 'var(--text-3)' }}>
              {' '}
              ({converted.value?.toFixed(2)} {converted.unit} / {other.value?.toFixed(2)} {other.unit})
            </span>
          )}
        </dd>

        <dt className="text-label uppercase text-text-3">Sources</dt>
        <dd className="m-0">
          <ul className="m-0 list-none p-0">
            {evidence.sources.map((s, i) => (
              <li key={i} className="font-mono text-label" style={{ color: 'var(--text-2)' }}>
                {s.file} <span style={{ color: 'var(--text-3)' }}>({shortSha(s.sha256)})</span>
                {s.channels && s.channels.length > 0 && <> · {s.channels.join(', ')}</>}
                {s.time_window && (
                  <> · [{s.time_window[0]}, {s.time_window[1]}]</>
                )}
              </li>
            ))}
          </ul>
        </dd>
      </dl>
      {evidence.sources[0]?.time_window && (
        <button
          type="button"
          className="mt-2 inline-block cursor-pointer text-label text-link underline-offset-2 hover:underline"
        >
          Show this window in the workspace
        </button>
      )}
    </div>
  )
}
