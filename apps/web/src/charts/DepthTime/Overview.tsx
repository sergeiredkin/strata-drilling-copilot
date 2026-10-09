// Full-well overview strip with a draggable/resizable brush — docs/02_IMPLEMENTATION_PLAN.md
// T6.3, comp S2-Workspace.dc.html. The brush represents the TrackStack's current window; drag
// to move, drag an edge to resize, or focus it and use arrow keys (Shift+arrow to resize).
import uPlot from 'uplot'
import { useEffect, useMemo, useRef, useState } from 'react'
import { useDepthTime, useSections } from '../../data/hooks'
import { clampRange, MIN_WINDOW_MS } from '../TrackStack/axes'
import type { TimeRangeSync } from '../TrackStack/sync'
import { useUplot } from '../TrackStack/useUplot'
import { sectionsPlugin, type SectionBand } from '../plugins/sections'

const STRIP_HEIGHT_PX = 64
const KEYBOARD_STEP_FRACTION = 0.02

export function Overview({
  wellId,
  fullRange,
  sync,
  onRangeSettled,
}: {
  wellId: string
  fullRange: [number, number]
  sync: TimeRangeSync
  onRangeSettled: (range: [number, number]) => void
}) {
  const containerRef = useRef<HTMLDivElement>(null)
  const depthTime = useDepthTime(wellId)
  const sections = useSections(wellId)
  const [range, setRangeState] = useState<[number, number]>(sync.getRange() ?? fullRange)

  useEffect(() => sync.subscribe((r) => setRangeState(r)), [sync])

  const sectionBands: SectionBand[] = useMemo(
    () => (sections.data ?? []).map((s) => ({ name: s.name, t0: s.t_start, t1: s.t_end })),
    [sections.data],
  )
  // See RibbonTrack.tsx: the uPlot instance (and its plugin) is built once and never remounted
  // on prop changes, so the plugin reads this ref rather than closing over sectionBands.
  const sectionBandsRef = useRef(sectionBands)
  sectionBandsRef.current = sectionBands

  const data: uPlot.AlignedData = useMemo(() => {
    if (!depthTime.data) return [[], []]
    return [depthTime.data.t, depthTime.data.hole_md]
  }, [depthTime.data])

  const buildOptions = useMemo(
    () => (width: number, height: number): uPlot.Options => ({
      width,
      height,
      padding: [4, 0, 0, 0],
      legend: { show: false },
      cursor: { show: false },
      scales: { x: { time: false, range: () => fullRange }, y: { dir: -1, auto: true } },
      axes: [{ show: false }, { show: false }],
      series: [{}, { stroke: 'var(--text)', width: 1.5, points: { show: false }, spanGaps: false }],
      plugins: [sectionsPlugin(() => sectionBandsRef.current)],
    }),
    [fullRange],
  )

  const uplotRef = useUplot(containerRef, { data, buildOptions, sync: undefined, fullRange, interactive: false })

  useEffect(() => {
    uplotRef.current?.setData(data)
  }, [data, uplotRef])
  useEffect(() => {
    uplotRef.current?.redraw()
  }, [sectionBands, uplotRef])

  const span = fullRange[1] - fullRange[0] || 1
  const leftPct = ((range[0] - fullRange[0]) / span) * 100
  const widthPct = ((range[1] - range[0]) / span) * 100

  const dragState = useRef<{ mode: 'move' | 'resize-left' | 'resize-right'; startX: number; startRange: [number, number] } | null>(null)

  function applyRange(next: [number, number]) {
    const clamped = clampRange(next[0], next[1], fullRange[0], fullRange[1])
    sync.setRange(clamped)
    onRangeSettled(clamped)
  }

  function onBrushPointerDown(mode: 'move' | 'resize-left' | 'resize-right') {
    return (e: React.PointerEvent) => {
      e.stopPropagation()
      dragState.current = { mode, startX: e.clientX, startRange: range }
      ;(e.target as HTMLElement).setPointerCapture(e.pointerId)
    }
  }

  function onBrushPointerMove(e: React.PointerEvent) {
    const drag = dragState.current
    if (!drag || !containerRef.current) return
    const rect = containerRef.current.getBoundingClientRect()
    const dxFrac = (e.clientX - drag.startX) / Math.max(rect.width, 1)
    const dt = dxFrac * span

    if (drag.mode === 'move') {
      applyRange([drag.startRange[0] + dt, drag.startRange[1] + dt])
    } else if (drag.mode === 'resize-left') {
      applyRange([drag.startRange[0] + dt, drag.startRange[1]])
    } else {
      applyRange([drag.startRange[0], drag.startRange[1] + dt])
    }
  }

  function onBrushPointerUp(e: React.PointerEvent) {
    dragState.current = null
    try {
      ;(e.target as HTMLElement).releasePointerCapture(e.pointerId)
    } catch {
      // already released
    }
  }

  function onBrushKeyDown(e: React.KeyboardEvent) {
    const step = span * KEYBOARD_STEP_FRACTION
    if (e.key === 'ArrowLeft') {
      e.preventDefault()
      if (e.shiftKey) applyRange([range[0], Math.max(range[1] - step, range[0] + MIN_WINDOW_MS)])
      else applyRange([range[0] - step, range[1] - step])
    } else if (e.key === 'ArrowRight') {
      e.preventDefault()
      if (e.shiftKey) applyRange([range[0], range[1] + step])
      else applyRange([range[0] + step, range[1] + step])
    }
  }

  return (
    <div className="flex flex-col gap-1.5 rounded border p-2.5" style={{ borderColor: 'var(--line)', background: 'var(--panel)' }}>
      <div className="flex flex-wrap items-center justify-between gap-2">
        <span className="font-condensed text-label uppercase text-text-3">
          Full well · depth vs time · drag to select
        </span>
        <span className="font-mono text-label text-text-3">{'▼'} casing shoe · shaded = hole section</span>
      </div>
      <div className="relative" style={{ height: STRIP_HEIGHT_PX }}>
        <div ref={containerRef} className="absolute inset-0" />
        <div
          role="slider"
          tabIndex={0}
          aria-label="Visible time window"
          aria-valuemin={fullRange[0]}
          aria-valuemax={fullRange[1]}
          aria-valuenow={(range[0] + range[1]) / 2}
          onKeyDown={onBrushKeyDown}
          onPointerDown={onBrushPointerDown('move')}
          onPointerMove={onBrushPointerMove}
          onPointerUp={onBrushPointerUp}
          className="absolute top-0 bottom-0 cursor-grab rounded-sm focus:outline focus:outline-2"
          style={{
            left: `${leftPct}%`,
            width: `${Math.max(widthPct, 0.5)}%`,
            background: 'rgba(245, 165, 36, .25)',
            border: '1px solid var(--accent)',
            outlineColor: 'var(--link)',
          }}
        >
          <div
            onPointerDown={onBrushPointerDown('resize-left')}
            onPointerMove={onBrushPointerMove}
            onPointerUp={onBrushPointerUp}
            className="absolute inset-y-0 left-0 w-1.5 cursor-ew-resize"
          />
          <div
            onPointerDown={onBrushPointerDown('resize-right')}
            onPointerMove={onBrushPointerMove}
            onPointerUp={onBrushPointerUp}
            className="absolute inset-y-0 right-0 w-1.5 cursor-ew-resize"
          />
        </div>
      </div>
    </div>
  )
}
