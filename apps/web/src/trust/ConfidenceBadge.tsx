// docs/05_DESIGN_SYSTEM.md §4. Reason is always available on hover/focus — via a real <button>
// (so it's keyboard-focusable) with both a native `title` and an aria-describedby tooltip, so
// the reason reaches both mouse and screen-reader users regardless of hover state.
import { useId } from 'react'
import type { Confidence } from '../contracts/types'

const GLYPH: Record<Confidence['level'], string> = {
  high: '▲',
  medium: '◆',
  low: '▼',
  insufficient: '○',
}

const LABEL: Record<Confidence['level'], string> = {
  high: 'High',
  medium: 'Medium',
  low: 'Low',
  insufficient: 'Insufficient data',
}

export function ConfidenceBadge({ c }: { c: Confidence }) {
  const descId = useId()

  return (
    <button
      type="button"
      className="group relative inline-flex items-center gap-1 rounded px-1.5 py-0.5 text-label font-mono"
      style={{
        background: `var(--confidence-${c.level}-bg)`,
        color: `var(--confidence-${c.level}-fg)`,
      }}
      title={c.reason}
      aria-describedby={descId}
    >
      <span aria-hidden="true">{GLYPH[c.level]}</span>
      <span>{LABEL[c.level]}</span>
      <span
        id={descId}
        role="tooltip"
        className="pointer-events-none absolute left-1/2 top-full z-10 mt-1 w-max max-w-64 -translate-x-1/2 rounded border p-2 text-left text-label opacity-0 shadow-lg group-hover:opacity-100 group-focus-visible:opacity-100"
        style={{ background: 'var(--panel)', borderColor: 'var(--line)', color: 'var(--text-2)' }}
      >
        {c.reason}
      </span>
    </button>
  )
}
