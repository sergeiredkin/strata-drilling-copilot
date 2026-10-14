// T13.3 — the replay event log drawer: every alert seen so far this replay session (06 S8).
import type { ReplayEvent } from '../../contracts/types'

function fmtTime(t: number): string {
  return new Date(t).toISOString().slice(0, 19).replace('T', ' ')
}

export function ReplayLog({ log, onClose }: { log: ReplayEvent[]; onClose: () => void }) {
  const alerts = log.filter((e): e is ReplayEvent & { type: 'alert' } => e.type === 'alert')
  return (
    <div
      role="dialog"
      aria-label="Replay event log"
      className="absolute right-0 top-full z-40 mt-1 w-[360px] max-h-[60vh] overflow-y-auto rounded border p-3"
      style={{ borderColor: 'var(--line)', background: 'var(--panel)' }}
    >
      <div className="mb-2 flex items-center justify-between">
        <span className="font-condensed text-label uppercase text-text-3">Event log</span>
        <button type="button" onClick={onClose} aria-label="Close event log" className="text-text-2 hover:text-text">
          ×
        </button>
      </div>
      {alerts.length === 0 ? (
        <p className="m-0 text-label text-text-2">No alerts yet this session.</p>
      ) : (
        <ul className="m-0 flex flex-col gap-1.5 p-0">
          {alerts.map((e) => (
            <li key={e.alert.id} className="flex flex-col gap-0.5 border-b pb-1.5 text-dense" style={{ borderColor: 'var(--line-soft)' }}>
              <span className="font-mono text-meta text-text-3">{fmtTime(e.t)}</span>
              <span>{e.alert.message}</span>
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}
