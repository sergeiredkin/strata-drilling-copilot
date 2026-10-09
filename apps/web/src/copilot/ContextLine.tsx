// "context · well · section · [t0]-[t1] · depth" — comp S2-Workspace.dc.html aside.
import type { CopilotContext } from '../contracts/types'

function fmtTime(ms: number): string {
  return new Date(ms).toISOString().replace('T', ' ').slice(0, 16)
}

export function ContextLine({ ctx }: { ctx: CopilotContext }) {
  const parts = [ctx.well ?? 'no well selected', ctx.section]
  if (ctx.time_window) {
    parts.push(`${fmtTime(ctx.time_window[0])}–${fmtTime(ctx.time_window[1])}`)
  }
  if (ctx.depth_window) {
    parts.push(`${ctx.depth_window[0].toFixed(0)}–${ctx.depth_window[1].toFixed(0)} m`)
  }

  return (
    <div
      className="rounded px-2.5 py-2 font-mono text-label leading-relaxed"
      style={{ background: 'var(--panel-2)', color: 'var(--text-2)' }}
    >
      context · {parts.filter(Boolean).join(' · ')}
    </div>
  )
}
