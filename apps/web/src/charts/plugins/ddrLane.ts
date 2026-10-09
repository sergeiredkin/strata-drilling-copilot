// DDR activity lane — bordered bars with code + truncated narrative, comp S2-Workspace.dc.html.
import type uPlot from 'uplot'

export type DdrLaneRow = { t0: number; t1: number; code: string; narrative: string }

const MIN_BAR_PX = 3
const PAD_Y = 4

function cssVar(name: string, fallback: string): string {
  if (typeof window === 'undefined') return fallback
  return getComputedStyle(document.documentElement).getPropertyValue(name).trim() || fallback
}

export function ddrLanePlugin(getRows: () => DdrLaneRow[]): uPlot.Plugin {
  return {
    hooks: {
      draw: [
        (u: uPlot) => {
          const rows = getRows()
          if (rows.length === 0) return

          const ctx = u.ctx
          const { left, top, width, height } = u.bbox
          ctx.save()
          ctx.beginPath()
          ctx.rect(left, top, width, height)
          ctx.clip()

          const fill = cssVar('--panel-2', '#1B2633')
          const border = cssVar('--line', '#3A4A5E')
          const text = cssVar('--text-2', '#C8D2DC')

          for (const row of rows) {
            const x0 = u.valToPos(row.t0, 'x', true)
            const x1 = u.valToPos(row.t1, 'x', true)
            const w = Math.max(x1 - x0, MIN_BAR_PX)
            const barTop = top + PAD_Y
            const barHeight = height - PAD_Y * 2

            ctx.fillStyle = fill
            ctx.strokeStyle = border
            ctx.lineWidth = 1
            roundRect(ctx, x0, barTop, w, barHeight, 3)
            ctx.fill()
            ctx.stroke()

            if (w >= 28) {
              const label = row.narrative ? `${row.code} — ${row.narrative}` : row.code
              ctx.save()
              ctx.font = '11px "IBM Plex Mono", monospace'
              ctx.fillStyle = text
              ctx.textBaseline = 'middle'
              ctx.textAlign = 'left'
              const maxChars = Math.max(Math.floor((w - 12) / 6.2), 0)
              const clipped = label.length > maxChars ? `${label.slice(0, Math.max(maxChars - 1, 0))}…` : label
              ctx.fillText(clipped, x0 + 6, top + height / 2)
              ctx.restore()
            }
          }

          ctx.restore()
        },
      ],
    },
  }
}

function roundRect(ctx: CanvasRenderingContext2D, x: number, y: number, w: number, h: number, r: number) {
  ctx.beginPath()
  ctx.moveTo(x + r, y)
  ctx.arcTo(x + w, y, x + w, y + h, r)
  ctx.arcTo(x + w, y + h, x, y + h, r)
  ctx.arcTo(x, y + h, x, y, r)
  ctx.arcTo(x, y, x + w, y, r)
  ctx.closePath()
}
