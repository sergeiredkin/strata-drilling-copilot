// Bit-depth-vs-time track — top of the stack in S2 (comp S2-Workspace.dc.html), 150px,
// inverted y (shallow at top, deep at bottom — docs/02_IMPLEMENTATION_PLAN.md T6.3).
import uPlot from 'uplot'
import { useEffect, useMemo, useRef } from 'react'
import { useDepthTime } from '../../data/hooks'
import { useCursor } from '../../state/cursor'
import { GUTTER_PX } from '../TrackStack/TrackStack'
import { HIDDEN_Y_AXIS, NO_X_AXIS } from '../TrackStack/axes'
import type { TimeRangeSync } from '../TrackStack/sync'
import { useUplot } from '../TrackStack/useUplot'
import { cursorLinePlugin } from '../plugins/cursorLine'

export const DEPTH_TRACK_HEIGHT_PX = 150

function lastDefined(values: (number | null)[]): number | null {
  for (let i = values.length - 1; i >= 0; i--) {
    const v = values[i]
    if (v !== undefined && v !== null) return v
  }
  return null
}

export function DepthTime({
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
  const cursorT = useCursor((s) => s.t)

  const data: uPlot.AlignedData = useMemo(() => {
    if (!depthTime.data) return [[], []]
    return [depthTime.data.t, depthTime.data.bit_md]
  }, [depthTime.data])

  const buildOptions = useMemo(
    () => (width: number, height: number): uPlot.Options => ({
      width,
      height,
      padding: [4, 0, 0, 0],
      legend: { show: false },
      cursor: { sync: { key: 'strata-s2' }, points: { show: false } },
      scales: { x: { time: false }, y: { dir: -1, auto: true } },
      axes: [NO_X_AXIS, HIDDEN_Y_AXIS],
      series: [{}, { stroke: 'var(--accent)', width: 2, points: { show: false }, spanGaps: false }],
      plugins: [cursorLinePlugin(false)],
    }),
    [],
  )

  const uplotRef = useUplot(containerRef, { data, buildOptions, sync, fullRange, onRangeSettled })

  useEffect(() => {
    uplotRef.current?.setData(data)
  }, [data, uplotRef])

  const cursorDepth = (() => {
    if (cursorT === null || !depthTime.data) return null
    const { t, bit_md } = depthTime.data
    let idx = -1
    for (let i = 0; i < t.length; i++) {
      if ((t[i] as number) <= cursorT) idx = i
      else break
    }
    return idx >= 0 ? (bit_md[idx] ?? null) : null
  })()

  const displayDepth = cursorDepth ?? (depthTime.data ? lastDefined(depthTime.data.bit_md) : null)

  return (
    <div className="flex border-b" style={{ borderColor: 'var(--line-soft)' }}>
      <div
        className="flex flex-none flex-col gap-px px-3 py-2"
        style={{ width: GUTTER_PX }}
      >
        <span className="font-condensed text-label uppercase text-text-3">Bit depth</span>
        <span className="font-mono text-meta text-text-3">m MD</span>
        <span className="font-mono text-dense">{displayDepth !== null ? displayDepth.toFixed(1) : '—'}</span>
      </div>
      <div ref={containerRef} className="relative flex-1" style={{ height: DEPTH_TRACK_HEIGHT_PX }} />
    </div>
  )
}
