// "▸ Tool trace · N calls · X s" drawer — comp S2-Workspace.dc.html. Steps stream in as
// tool_call/tool_result events arrive; expands to show tool, args, ms, status, result summary.
import { useState } from 'react'
import type { TraceStep } from '../contracts/types'

export function ToolTrace({ steps }: { steps: TraceStep[] }) {
  const [open, setOpen] = useState(false)
  const totalMs = steps.reduce((sum, s) => sum + s.ms, 0)

  return (
    <div className="flex flex-col gap-1.5">
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        className="flex min-h-10 items-center justify-between rounded border px-3 text-dense"
        style={{ borderColor: 'var(--line)', background: 'var(--panel-2)', color: 'var(--text)' }}
        aria-expanded={open}
      >
        <span>
          {open ? '▾' : '▸'} Tool trace · {steps.length} call{steps.length === 1 ? '' : 's'}
        </span>
        <span className="font-mono text-label" style={{ color: 'var(--text-2)' }}>
          {(totalMs / 1000).toFixed(1)} s
        </span>
      </button>
      {open && (
        <ol className="m-0 flex list-none flex-col gap-1.5 p-0">
          {steps.map((step) => (
            <li
              key={step.i}
              className="rounded border p-2 font-mono text-label leading-relaxed"
              style={{ borderColor: 'var(--line)', color: 'var(--text-2)' }}
            >
              <div style={{ color: step.status === 'error' ? 'var(--danger)' : 'var(--text)' }}>
                {step.status === 'error' ? '✕' : '✓'} {step.tool} · {step.ms} ms
              </div>
              <div className="whitespace-pre-wrap">{JSON.stringify(step.args)}</div>
              {step.result_summary && <div>{step.result_summary}</div>}
              {step.evidence_ids && step.evidence_ids.length > 0 && (
                <div>evidence {step.evidence_ids.join(', ')}</div>
              )}
            </li>
          ))}
        </ol>
      )}
    </div>
  )
}
