// "Suggested for this view" chips — recorded sessions matching the current screen+well in
// static mode (docs/06_SCREENS.md S4). Live mode would generate these per screen instead.
import type { CopilotContext, SessionIndex } from '../contracts/types'

export function Suggestions({
  sessions,
  ctx,
  excludeId,
  onPick,
}: {
  sessions: SessionIndex
  ctx: CopilotContext
  excludeId?: string
  onPick: (sessionId: string, question: string) => void
}) {
  const matches = sessions.sessions.filter(
    (s) =>
      s.id !== excludeId &&
      s.context.screen === ctx.screen &&
      (!ctx.well || !s.context.well || s.context.well === ctx.well),
  )

  if (matches.length === 0) return null

  return (
    <div className="flex flex-col gap-1.5">
      <span className="font-condensed text-label uppercase text-text-3">Suggested for this view</span>
      <div className="flex flex-wrap gap-1.5">
        {matches.map((s) => (
          <button
            key={s.id}
            type="button"
            onClick={() => onPick(s.id, s.question)}
            className="rounded border px-2.5 py-1 text-label"
            style={{ borderColor: 'var(--line)', background: 'var(--panel)', color: 'var(--text)' }}
          >
            {s.question}
          </button>
        ))}
      </div>
    </div>
  )
}
