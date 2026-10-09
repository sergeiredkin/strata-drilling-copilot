// Mismatch ▲ markers + click hit-testing — docs/06_SCREENS.md S2 ("mismatch marker click ->
// popover"). Drawn just above the DDR lane; a real pointer listener (not just a draw-time
// decoration) so the popover can open on click. Listens for `pointerdown`, not `click` — a
// bare, directly-dispatched `click` MouseEvent was observed not reaching listeners on this
// element at all (plain `mousedown`/`pointerdown` did), most likely swallowed by React's
// delegated event system; `pointerdown` also matches the press-driven interaction model the
// rest of the chart (wheel-zoom, drag-pan in useUplot.ts) already uses.
import type uPlot from 'uplot'

export type MismatchMarker = { id: string; t0: number; t1: number }

const MARKER_SIZE = 11
const MARKER_Y_OFFSET = 10 // CSS px above the lane's top edge

export function mismatchPlugin(
  getMarkers: () => MismatchMarker[],
  onMarkerClick: (id: string) => void,
): uPlot.Plugin {
  let attachedOver: HTMLDivElement | null = null
  let downHandler: ((e: PointerEvent) => void) | null = null

  // `canvasPixels=true` (device-pixel space, what ctx.* drawing needs) for draw; `false`
  // (CSS-pixel space, matches PointerEvent.clientX/getBoundingClientRect) for hit-testing —
  // mixing the two silently breaks hit-testing on any display with devicePixelRatio != 1.
  function markerXs(u: uPlot, canvasPixels: boolean): { id: string; x: number }[] {
    return getMarkers().map((m) => ({
      id: m.id,
      x: u.valToPos((m.t0 + m.t1) / 2, 'x', canvasPixels),
    }))
  }

  return {
    hooks: {
      draw: [
        (u: uPlot) => {
          const dpr = window.devicePixelRatio || 1
          const ctx = u.ctx
          const y = u.bbox.top - MARKER_Y_OFFSET * dpr
          const size = MARKER_SIZE * dpr
          ctx.save()
          for (const { x } of markerXs(u, true)) {
            if (x < u.bbox.left - size || x > u.bbox.left + u.bbox.width + size) continue
            ctx.beginPath()
            ctx.moveTo(x, y - size / 2)
            ctx.lineTo(x + size / 2, y + size / 2)
            ctx.lineTo(x - size / 2, y + size / 2)
            ctx.closePath()
            ctx.fillStyle = '#FF6B6B'
            ctx.strokeStyle = '#0A0E13'
            ctx.lineWidth = 1.5 * dpr
            ctx.fill()
            ctx.stroke()
            ctx.fillStyle = '#0A0E13'
            ctx.font = `700 ${9 * dpr}px "IBM Plex Mono", monospace`
            ctx.textAlign = 'center'
            ctx.textBaseline = 'middle'
            ctx.fillText('!', x, y + 2 * dpr)
          }
          ctx.restore()
        },
      ],
      ready: [
        (u: uPlot) => {
          downHandler = (e: PointerEvent) => {
            const rect = u.over.getBoundingClientRect()
            const px = e.clientX - rect.left
            const py = e.clientY - rect.top
            const yCss = u.bbox.top / (window.devicePixelRatio || 1) - MARKER_Y_OFFSET
            for (const { id, x } of markerXs(u, false)) {
              if (Math.abs(px - x) <= MARKER_SIZE && Math.abs(py - yCss) <= MARKER_SIZE) {
                e.stopImmediatePropagation() // don't let useUplot's own pointerdown start a drag-pan too
                onMarkerClick(id)
                return
              }
            }
          }
          u.over.addEventListener('pointerdown', downHandler, true)
          attachedOver = u.over
        },
      ],
      destroy: [
        () => {
          if (attachedOver && downHandler) attachedOver.removeEventListener('pointerdown', downHandler, true)
        },
      ],
    },
  }
}
