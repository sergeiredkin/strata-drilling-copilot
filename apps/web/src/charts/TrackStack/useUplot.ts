// Creates/destroys one uPlot instance, wires wheel-zoom-around-cursor and drag-to-pan (clamped
// to [2 min, full well]), keeps it in sync with sibling tracks via a TimeRangeSync, resizes with
// its container, and feeds the shared cursor store so the 148px gutter readouts update on hover.
import uPlot from 'uplot'
import { useEffect, useRef } from 'react'
import { useCursor } from '../../state/cursor'
import { clampRange, MIN_WINDOW_MS } from './axes'
import type { TimeRangeSync } from './sync'

export type UseUplotOptions = {
  data: uPlot.AlignedData
  buildOptions: (width: number, height: number) => uPlot.Options
  sync?: TimeRangeSync
  fullRange: [number, number]
  onRangeSettled?: (range: [number, number]) => void
  /** Disables wheel/drag interaction on this track (e.g. the overview strip has its own brush). */
  interactive?: boolean
}

const ZOOM_FACTOR = 0.85 // per wheel notch

export function useUplot(containerRef: React.RefObject<HTMLDivElement | null>, opts: UseUplotOptions) {
  const uplotRef = useRef<uPlot | null>(null)
  const originRef = useRef(Symbol('track'))
  const dragRef = useRef<{ startX: number; startRange: [number, number] } | null>(null)
  const settleTimer = useRef<ReturnType<typeof setTimeout> | null>(null)
  const optsRef = useRef(opts)
  optsRef.current = opts

  useEffect(() => {
    const container = containerRef.current
    if (!container) return undefined

    const width = container.clientWidth || 300
    const height = container.clientHeight || 54
    const u = new uPlot(opts.buildOptions(width, height), opts.data, container)
    uplotRef.current = u
    // Tracks the "live" range synchronously across a fast burst of wheel/pointer events — uPlot
    // batches u.scales.x updates onto a rAF, so reading u.scales.x mid-burst can return a stale
    // value and collapse many zoom steps into one. This ref is always current.
    const currentRange = { current: [...(opts.sync?.getRange() ?? opts.fullRange)] as [number, number] }

    const resizeObserver = new ResizeObserver(() => {
      if (!container.clientWidth) return
      u.setSize({ width: container.clientWidth, height: container.clientHeight })
    })
    resizeObserver.observe(container)

    const unsubscribe = opts.sync?.subscribe((range, origin) => {
      if (origin === originRef.current) return
      currentRange.current = range
      u.setScale('x', { min: range[0], max: range[1] })
    })

    function scheduleSettle(range: [number, number]) {
      if (settleTimer.current) clearTimeout(settleTimer.current)
      settleTimer.current = setTimeout(() => optsRef.current.onRangeSettled?.(range), 250)
    }

    function applyRange(range: [number, number]) {
      const clamped = clampRange(range[0], range[1], optsRef.current.fullRange[0], optsRef.current.fullRange[1])
      currentRange.current = clamped
      u.setScale('x', { min: clamped[0], max: clamped[1] })
      optsRef.current.sync?.setRange(clamped, originRef.current)
      scheduleSettle(clamped)
    }

    function onWheel(e: WheelEvent) {
      if (optsRef.current.interactive === false) return
      e.preventDefault()
      const rect = u.over.getBoundingClientRect()
      const cursorVal = u.posToVal(e.clientX - rect.left, 'x')
      const [min, max] = currentRange.current
      const factor = e.deltaY > 0 ? 1 / ZOOM_FACTOR : ZOOM_FACTOR
      const newMin = cursorVal - (cursorVal - min) * factor
      const newMax = cursorVal + (max - cursorVal) * factor
      applyRange([newMin, newMax])
    }

    function onPointerDown(e: PointerEvent) {
      if (optsRef.current.interactive === false) return
      if (e.button !== 0) return
      dragRef.current = { startX: e.clientX, startRange: [...currentRange.current] as [number, number] }
      u.over.setPointerCapture(e.pointerId)
    }

    function onPointerMove(e: PointerEvent) {
      const drag = dragRef.current
      if (drag) {
        const rect = u.over.getBoundingClientRect()
        const scaleSpan = drag.startRange[1] - drag.startRange[0]
        const perPx = scaleSpan / Math.max(rect.width, 1)
        const dx = (e.clientX - drag.startX) * perPx
        applyRange([drag.startRange[0] - dx, drag.startRange[1] - dx])
        return
      }
      const rect = u.over.getBoundingClientRect()
      if (e.clientX < rect.left || e.clientX > rect.right) return
      const t = u.posToVal(e.clientX - rect.left, 'x')
      useCursor.getState().setT(t)
    }

    function onPointerUp(e: PointerEvent) {
      dragRef.current = null
      try {
        u.over.releasePointerCapture(e.pointerId)
      } catch {
        // already released
      }
    }

    function onMouseLeave() {
      useCursor.getState().setT(null)
    }

    u.over.addEventListener('wheel', onWheel, { passive: false })
    u.over.addEventListener('pointerdown', onPointerDown)
    u.over.addEventListener('pointermove', onPointerMove)
    u.over.addEventListener('pointerup', onPointerUp)
    u.over.addEventListener('mouseleave', onMouseLeave)

    return () => {
      resizeObserver.disconnect()
      unsubscribe?.()
      if (settleTimer.current) clearTimeout(settleTimer.current)
      u.over.removeEventListener('wheel', onWheel)
      u.over.removeEventListener('pointerdown', onPointerDown)
      u.over.removeEventListener('pointermove', onPointerMove)
      u.over.removeEventListener('pointerup', onPointerUp)
      u.over.removeEventListener('mouseleave', onMouseLeave)
      u.destroy()
      uplotRef.current = null
    }
    // Intentionally re-run only when the container or the static buildOptions identity changes —
    // live data updates go through uplotRef.current.setData() from the caller, not a remount.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [containerRef])

  return uplotRef
}

export { MIN_WINDOW_MS }
