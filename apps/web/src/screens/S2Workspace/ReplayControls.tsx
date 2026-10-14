// T13.3 — S2 header controls: play/pause, 1x/10x/60x, time readout (06 S8).
import { useState } from 'react'
import type { ReplaySpeed } from '../../state/replay'
import { useReplay } from '../../state/replay'
import { ReplayLog } from './ReplayLog'

const SPEEDS: ReplaySpeed[] = [1, 10, 60]

function fmtReadout(t: number | null): string {
  if (t === null) return '—'
  return new Date(t).toISOString().slice(0, 19).replace('T', ' ')
}

export function ReplayControls({ onPlay, onPause }: { onPlay: () => void; onPause: () => void }) {
  const playing = useReplay((s) => s.playing)
  const speed = useReplay((s) => s.speed)
  const setSpeed = useReplay((s) => s.setSpeed)
  const t = useReplay((s) => s.t)
  const log = useReplay((s) => s.log)
  const [logOpen, setLogOpen] = useState(false)

  return (
    <div className="flex flex-wrap items-center gap-1.5">
      <button
        type="button"
        onClick={() => (playing ? onPause() : onPlay())}
        aria-pressed={playing}
        className="min-h-9 rounded border px-3 text-dense"
        style={{ borderColor: playing ? 'var(--accent)' : 'var(--line)', background: 'var(--panel)' }}
      >
        {playing ? '⏸ Pause' : '▶ Replay'}
      </button>
      <div className="flex gap-0.5" role="group" aria-label="Replay speed">
        {SPEEDS.map((s) => (
          <button
            key={s}
            type="button"
            onClick={() => setSpeed(s)}
            aria-pressed={speed === s}
            className="min-h-9 rounded border px-2.5 text-dense"
            style={{ borderColor: speed === s ? 'var(--accent)' : 'var(--line)', background: 'var(--panel)' }}
          >
            {s}×
          </button>
        ))}
      </div>
      <span className="font-mono text-dense text-text-2">{fmtReadout(t)}</span>
      <button
        type="button"
        onClick={() => setLogOpen((o) => !o)}
        aria-pressed={logOpen}
        className="min-h-9 rounded border px-3 text-dense"
        style={{ borderColor: logOpen ? 'var(--accent)' : 'var(--line)', background: 'var(--panel)' }}
      >
        Event log {log.length > 0 && `(${log.length})`}
      </button>
      {logOpen && <ReplayLog log={log} onClose={() => setLogOpen(false)} />}
    </div>
  )
}
