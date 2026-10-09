// Rig-state ribbon — docs/02_IMPLEMENTATION_PLAN.md T6.4: dominant state per pixel column when
// intervals are narrower than 1px, CanvasPattern fills, labels when a segment is >=56px wide.
import type uPlot from 'uplot'
import type { RigState } from '../../contracts/types'
import { rigStateLabelColor, rigStateStyle, RIG_STATE_LABEL } from './rigStateStyle'

export type RibbonInterval = { t0: number; t1: number; state: RigState }

const LABEL_MIN_PX = 56

export function ribbonPlugin(getIntervals: () => RibbonInterval[]): uPlot.Plugin {
  return {
    hooks: {
      draw: [
        (u: uPlot) => {
          const intervals = getIntervals()
          if (intervals.length === 0) return

          const ctx = u.ctx
          const { left, top, width, height } = u.bbox
          ctx.save()
          ctx.beginPath()
          ctx.rect(left, top, width, height)
          ctx.clip()

          const scaleMin = u.scales.x?.min
          const scaleMax = u.scales.x?.max
          if (scaleMin == null || scaleMax == null) {
            ctx.restore()
            return
          }
          const msPerPx = (scaleMax - scaleMin) / Math.max(width, 1)

          // If the average interval covers < 1px, aggregate into per-pixel-column dominant
          // state first; otherwise draw each interval directly (cheaper and crisper).
          const visible = intervals.filter((iv) => iv.t1 > scaleMin && iv.t0 < scaleMax)
          const avgPx = visible.length ? width / visible.length : width

          if (avgPx >= 1) {
            for (const iv of visible) {
              const x0 = u.valToPos(iv.t0, 'x', true)
              const x1 = u.valToPos(iv.t1, 'x', true)
              drawSegment(ctx, x0, x1, top, height, iv.state)
            }
          } else {
            const columns = new Array<RigState | null>(Math.ceil(width))
            for (let px = 0; px < width; px++) {
              const t = scaleMin + px * msPerPx
              const iv = visible.find((v) => v.t0 <= t && t < v.t1)
              columns[px] = iv?.state ?? null
            }
            // Run-length encode the column array so we still draw contiguous rects (crisper
            // than 1 fillRect per px) and can still fit labels on wide runs.
            let runStart = 0
            for (let px = 1; px <= columns.length; px++) {
              if (px === columns.length || columns[px] !== columns[runStart]) {
                const state = columns[runStart]
                if (state) drawSegment(ctx, left + runStart, left + px, top, height, state)
                runStart = px
              }
            }
          }

          ctx.restore()
        },
      ],
    },
  }
}

function drawSegment(
  ctx: CanvasRenderingContext2D,
  x0: number,
  x1: number,
  top: number,
  height: number,
  state: RigState,
) {
  const w = x1 - x0
  if (w <= 0) return
  ctx.fillStyle = rigStateStyle(ctx, state)
  ctx.fillRect(x0, top, w, height)

  if (w >= LABEL_MIN_PX) {
    ctx.save()
    ctx.font = '600 10.5px "IBM Plex Sans Condensed", sans-serif'
    ctx.fillStyle = rigStateLabelColor(state)
    ctx.textAlign = 'center'
    ctx.textBaseline = 'middle'
    ctx.fillText(RIG_STATE_LABEL[state].toUpperCase(), x0 + w / 2, top + height / 2, w - 6)
    ctx.restore()
  }
}
