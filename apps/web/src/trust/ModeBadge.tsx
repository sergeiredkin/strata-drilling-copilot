// docs/05_DESIGN_SYSTEM.md §6: "STATIC MODE" / "LIVE". Nav.tsx used an inline copy before this
// task existed (T4.2); this is the real component, now imported there instead.
import { isLiveMode } from '../data/createDataSource'

export function ModeBadge() {
  const live = isLiveMode()
  return (
    <span
      className="rounded border px-2 py-0.5 text-label font-mono uppercase tracking-wide"
      style={{
        borderColor: 'var(--line)',
        color: live ? 'var(--ok)' : 'var(--mock-fg)',
        background: live ? 'transparent' : 'var(--mock-bg)',
      }}
    >
      {live ? 'Live' : 'Static mode'}
    </span>
  )
}
