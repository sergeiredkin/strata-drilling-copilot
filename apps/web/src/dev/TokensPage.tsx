import { useState } from 'react'

const BASE_TOKENS = [
  'bg',
  'bg-nav',
  'panel',
  'panel-2',
  'line',
  'line-soft',
  'text',
  'text-2',
  'text-3',
  'accent',
  'link',
  'danger',
  'ok',
  'mock-bg',
  'mock-fg',
]

const STATE_TOKENS = [
  'rotary-drilling',
  'sliding',
  'connection',
  'trip-in',
  'trip-out',
  'reaming',
  'circulating',
  'out-of-hole',
  'unknown',
]

const CONFIDENCE_LEVELS = ['high', 'medium', 'low', 'insufficient']

function Swatch({ varName, label }: { varName: string; label: string }) {
  return (
    <div className="flex items-center gap-2 rounded border border-line p-2">
      <div
        className="h-8 w-8 flex-none rounded border border-line"
        style={{ background: `var(--${varName})` }}
      />
      <div>
        <div className="font-mono text-dense text-text">--{varName}</div>
        <div className="text-label text-text-3">{label}</div>
      </div>
    </div>
  )
}

function ThemeColumn({ theme }: { theme: 'dark' | 'light' }) {
  return (
    <div data-theme={theme} className="flex-1 rounded border border-line bg-bg p-4">
      <h2 className="mb-3 font-condensed text-card-title uppercase tracking-wide text-text">
        {theme}
      </h2>

      <h3 className="mb-2 text-meta uppercase text-text-3">Base</h3>
      <div className="mb-4 grid grid-cols-2 gap-2">
        {BASE_TOKENS.map((t) => (
          <Swatch key={t} varName={t} label={t} />
        ))}
      </div>

      <h3 className="mb-2 text-meta uppercase text-text-3">Rig state</h3>
      <div className="mb-4 grid grid-cols-2 gap-2">
        {STATE_TOKENS.map((s) => (
          <Swatch key={s} varName={`state-${s}-fill`} label={s} />
        ))}
      </div>

      <h3 className="mb-2 text-meta uppercase text-text-3">Confidence</h3>
      <div className="grid grid-cols-2 gap-2">
        {CONFIDENCE_LEVELS.map((level) => (
          <div
            key={level}
            className="rounded border border-line p-2 text-dense"
            style={{
              background: `var(--confidence-${level}-bg)`,
              color: `var(--confidence-${level}-fg)`,
            }}
          >
            {level}
          </div>
        ))}
      </div>
    </div>
  )
}

export function TokensPage() {
  const [side, setSide] = useState<'both' | 'dark' | 'light'>('both')

  return (
    <div className="min-h-screen bg-bg p-6 text-text">
      <h1 className="mb-4 text-page-title">Design tokens — dev only</h1>
      <div className="mb-4 flex gap-2">
        {(['both', 'dark', 'light'] as const).map((s) => (
          <button
            key={s}
            type="button"
            onClick={() => setSide(s)}
            className="min-h-9 rounded border border-line px-3 text-dense"
            aria-pressed={side === s}
          >
            {s}
          </button>
        ))}
      </div>
      <div className="flex gap-4">
        {(side === 'both' || side === 'dark') && <ThemeColumn theme="dark" />}
        {(side === 'both' || side === 'light') && <ThemeColumn theme="light" />}
      </div>
    </div>
  )
}
