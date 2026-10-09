// Vertical cursor line + a time chip at the top of the plot — docs/06_SCREENS.md S2 "Overlays
// across the whole stack: ... cursor line + time chip." uPlot's native crosshair handles the
// cross-track sync (cursor.sync); this plugin only adds the chip label + a brighter/thicker
// line than the native default so it reads clearly against the dark theme.
import type uPlot from 'uplot'
import { formatTimeFull } from '../TrackStack/axes'

function cssVar(name: string, fallback: string): string {
  if (typeof window === 'undefined') return fallback
  return getComputedStyle(document.documentElement).getPropertyValue(name).trim() || fallback
}

export function cursorLinePlugin(showChip = false): uPlot.Plugin {
  return {
    hooks: {
      draw: [
        (u: uPlot) => {
          const { left: cursorLeft, idx } = u.cursor
          if (cursorLeft == null || cursorLeft < 0 || idx == null) return

          const { top, height, left: bboxLeft, width } = u.bbox
          const x = bboxLeft + cursorLeft
          if (x < bboxLeft || x > bboxLeft + width) return

          const ctx = u.ctx
          ctx.save()
          ctx.strokeStyle = cssVar('--link', '#7CC4FF')
          ctx.lineWidth = 1
          ctx.beginPath()
          ctx.moveTo(x, top)
          ctx.lineTo(x, top + height)
          ctx.stroke()

          if (showChip) {
            const tVal = u.data[0]?.[idx]
            if (tVal != null) {
              const label = formatTimeFull(tVal)
              ctx.font = '11px "IBM Plex Mono", monospace'
              const textWidth = ctx.measureText(label).width
              const chipX = Math.min(Math.max(x - textWidth / 2 - 6, bboxLeft), bboxLeft + width - textWidth - 12)
              ctx.fillStyle = cssVar('--text', '#F5F7FA')
              ctx.fillRect(chipX, top - 18, textWidth + 12, 16)
              ctx.fillStyle = cssVar('--bg', '#0A0E13')
              ctx.textBaseline = 'middle'
              ctx.textAlign = 'left'
              ctx.fillText(label, chipX + 6, top - 10)
            }
          }
          ctx.restore()
        },
      ],
    },
  }
}
