// Mismatch marker click popover — comp S2-Workspace.dc.html: Sensors say | Report says,
// overlap %, tolerance, "Zoom to window" / "Ask copilot why".
import type { Mismatch } from '../../contracts/types'
import { RIG_STATE_LABEL } from '../../charts/plugins/rigStateStyle'
import { Num } from '../../trust/Num'

export function MismatchPopover({
  mismatch,
  narrative,
  reportDate,
  onClose,
  onZoomToWindow,
  onAskCopilot,
}: {
  mismatch: Mismatch
  narrative: string
  reportDate: string
  onClose: () => void
  onZoomToWindow: () => void
  onAskCopilot: () => void
}) {
  const durationMin = Math.round((mismatch.t1 - mismatch.t0) / 60_000)

  return (
    <div
      role="dialog"
      aria-label="Mismatch details"
      className="flex w-[420px] max-w-[80vw] flex-col gap-2.5 rounded-md border p-3.5 shadow-lg"
      style={{ background: 'var(--bg-nav)', borderColor: 'var(--danger)' }}
    >
      <div className="flex items-center justify-between">
        <span className="font-condensed text-label uppercase" style={{ color: 'var(--confidence-low-fg)' }}>
          Mismatch · {durationMin} min
        </span>
        <div className="flex items-center gap-2">
          <span className="font-mono text-label text-text-3">
            overlap {mismatch.overlap_pct.toFixed(0)}% · min dur {mismatch.tolerance?.min_duration_min ?? 2} min
          </span>
          <button type="button" onClick={onClose} aria-label="Close" className="text-text-3 hover:text-text">
            {'✕'}
          </button>
        </div>
      </div>

      <div className="grid grid-cols-2 gap-2.5">
        <div className="flex flex-col gap-1 rounded p-2.5" style={{ background: 'var(--panel)' }}>
          <span className="font-condensed text-label uppercase text-text-3">Sensors say</span>
          <span className="text-body font-semibold" style={{ color: 'var(--ok)' }}>
            {RIG_STATE_LABEL[mismatch.sensor_state]}
          </span>
          <span className="text-meta leading-relaxed text-text-2">
            Classifier confidence {mismatch.sensor_p?.toFixed(2) ?? '—'}.
          </span>
        </div>
        <div className="flex flex-col gap-1 rounded p-2.5" style={{ background: 'var(--panel)' }}>
          <span className="font-condensed text-label uppercase text-text-3">Report says</span>
          <span className="text-body font-semibold text-text">{mismatch.ddr_code}</span>
          <span className="text-meta italic leading-relaxed text-text-2">
            &ldquo;{narrative}&rdquo; — DDR {reportDate}
          </span>
        </div>
      </div>

      <div className="text-label text-text-3">
        Duration <Num q={mismatch.duration} showUnit />
      </div>

      <div className="flex flex-wrap gap-2">
        <button
          type="button"
          onClick={onZoomToWindow}
          className="min-h-9 rounded border px-3 text-dense"
          style={{ borderColor: 'var(--line)', background: 'var(--panel)' }}
        >
          Zoom to window
        </button>
        <button
          type="button"
          onClick={onAskCopilot}
          className="min-h-9 rounded border px-3 text-dense"
          style={{ borderColor: 'var(--line)', background: 'var(--panel)' }}
        >
          Ask copilot why
        </button>
      </div>
    </div>
  )
}
