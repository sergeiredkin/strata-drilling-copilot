// Draws a 45° hatch over null (no-data) runs in series[1] (the band's min), with a
// "no data · N min" label when the gap is >= 40px wide — docs/03_ARCHITECTURE.md §3.3,
// docs/05_DESIGN_SYSTEM.md §3 (gap pattern). Gaps are derived straight from the plotted data's
// null runs, so hatching always matches exactly what's NOT drawn — "gaps are never interpolated"
// stays true by construction, not by a second data source that could drift from the first.
import type uPlot from 'uplot'

const LABEL_MIN_PX = 40

function cssVar(name: string): string {
  if (typeof window === 'undefined') return '#3A4552'
  return getComputedStyle(document.documentElement).getPropertyValue(name).trim() || '#3A4552'
}

export function gapHatchPlugin(seriesIdx = 1): uPlot.Plugin {
  return {
    hooks: {
      draw: [
        (u: uPlot) => {
          const xData = u.data[0]
          const yData = u.data[seriesIdx]
          if (!xData || !yData) return

          const ctx = u.ctx
          const { left, top, width, height } = u.bbox
          ctx.save()
          ctx.beginPath()
          ctx.rect(left, top, width, height)
          ctx.clip()

          const hatchColor = cssVar('--line')
          const bgColor = cssVar('--panel-2')

          let runStart = -1
          for (let i = 0; i <= xData.length; i++) {
            const isNull = i < xData.length && (yData[i] === null || yData[i] === undefined)
            if (isNull && runStart === -1) {
              runStart = i
            } else if (!isNull && runStart !== -1) {
              drawHatch(u, ctx, xData, runStart, i - 1, hatchColor, bgColor)
              runStart = -1
            }
          }

          ctx.restore()
        },
      ],
    },
  }
}

function drawHatch(
  u: uPlot,
  ctx: CanvasRenderingContext2D,
  xData: ArrayLike<number | null | undefined>,
  startIdx: number,
  endIdx: number,
  hatchColor: string,
  bgColor: string,
) {
  const t0 = xData[startIdx]
  const t1 = xData[endIdx]
  if (t0 == null || t1 == null) return

  const x0 = u.valToPos(t0, 'x', true)
  const x1 = u.valToPos(t1, 'x', true)
  const { top, height } = u.bbox
  const w = Math.max(x1 - x0, 1)

  ctx.save()
  ctx.beginPath()
  ctx.rect(x0, top, w, height)
  ctx.clip()
  ctx.fillStyle = bgColor
  ctx.fillRect(x0, top, w, height)

  ctx.strokeStyle = hatchColor
  ctx.lineWidth = 1
  const step = 7
  for (let x = x0 - height; x < x1 + height; x += step) {
    ctx.beginPath()
    ctx.moveTo(x, top + height)
    ctx.lineTo(x + height, top)
    ctx.stroke()
  }
  ctx.restore()

  if (w >= LABEL_MIN_PX) {
    const minutes = Math.round((t1 - t0) / 60_000)
    const label = `no data · ${minutes} min`
    ctx.save()
    ctx.font = '10.5px "IBM Plex Mono", monospace'
    ctx.fillStyle = cssVar('--text-2')
    ctx.textBaseline = 'middle'
    ctx.textAlign = 'center'
    ctx.fillText(label, x0 + w / 2, top + height / 2)
    ctx.restore()
  }
}
