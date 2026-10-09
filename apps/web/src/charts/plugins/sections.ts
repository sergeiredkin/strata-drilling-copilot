// Shades the background by hole section — used by DepthTime/Overview (T6.3). Alternates two
// faint panel tones so adjacent sections are visually distinguishable without competing with
// the series strokes, and labels each band when it's wide enough to hold text.
import type uPlot from 'uplot'

export type SectionBand = {
  name: string
  t0: number
  t1: number
}

const LABEL_MIN_PX = 36

function cssVar(name: string): string {
  if (typeof window === 'undefined') return '#161D25'
  return getComputedStyle(document.documentElement).getPropertyValue(name).trim() || '#161D25'
}

export function sectionsPlugin(getSections: () => SectionBand[]): uPlot.Plugin {
  return {
    hooks: {
      draw: [
        (u: uPlot) => {
          const sections = getSections()
          if (sections.length === 0) return

          const ctx = u.ctx
          const { left, top, width, height } = u.bbox
          ctx.save()
          ctx.beginPath()
          ctx.rect(left, top, width, height)
          ctx.clip()

          const toneA = cssVar('--panel')
          const toneB = cssVar('--panel-2')
          const lineColor = cssVar('--line')
          const textColor = cssVar('--text-2')

          sections.forEach((s, i) => {
            const x0 = u.valToPos(s.t0, 'x', true)
            const x1 = u.valToPos(s.t1, 'x', true)
            const w = x1 - x0
            if (w <= 0) return

            ctx.fillStyle = i % 2 === 0 ? toneA : toneB
            ctx.fillRect(x0, top, w, height)
            ctx.strokeStyle = lineColor
            ctx.beginPath()
            ctx.moveTo(x1, top)
            ctx.lineTo(x1, top + height)
            ctx.stroke()

            if (w >= LABEL_MIN_PX) {
              ctx.font = '11px "IBM Plex Mono", monospace'
              ctx.fillStyle = textColor
              ctx.textBaseline = 'top'
              ctx.textAlign = 'left'
              ctx.fillText(s.name, x0 + 6, top + 3)
            }
          })

          ctx.restore()
        },
      ],
    },
  }
}
