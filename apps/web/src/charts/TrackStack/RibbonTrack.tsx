// Rig-state ribbon row — comp S2-Workspace.dc.html ("Rig state" / current state label + ribbon).
import uPlot from 'uplot'
import { useEffect, useMemo, useRef } from 'react'
import type { RigStateInterval } from '../../contracts/types'
import { useCursor } from '../../state/cursor'
import { ribbonPlugin, type RibbonInterval } from '../plugins/ribbon'
import { RIG_STATE_LABEL } from '../plugins/rigStateStyle'
import { HIDDEN_Y_AXIS, NO_X_AXIS } from './axes'
import type { TimeRangeSync } from './sync'
import { GUTTER_PX } from './TrackStack'
import { useUplot } from './useUplot'

export const RIBBON_HEIGHT_PX = 40

export function RibbonTrack({
  intervals,
  fullRange,
  sync,
  onRangeSettled,
}: {
  intervals: RigStateInterval[]
  fullRange: [number, number]
  sync: TimeRangeSync
  onRangeSettled: (range: [number, number]) => void
}) {
  const containerRef = useRef<HTMLDivElement>(null)
  const cursorT = useCursor((s) => s.t)

  const ribbonIntervals: RibbonInterval[] = useMemo(
    () => intervals.map((iv) => ({ t0: iv.t0, t1: iv.t1, state: iv.state })),
    [intervals],
  )
  // The uPlot instance (and the plugin baked into it) is created once; useUplot never remounts
  // it on prop changes. The plugin reads this ref's `.current` on every draw instead of closing
  // over `ribbonIntervals` directly, so fresh data (e.g. the query resolving after mount) is
  // visible without recreating the chart — we just redraw() when it changes (effect below).
  const intervalsRef = useRef(ribbonIntervals)
  intervalsRef.current = ribbonIntervals

  const data: uPlot.AlignedData = useMemo(() => [fullRange, [null, null]], [fullRange])

  const buildOptions = useMemo(
    () => (width: number, height: number): uPlot.Options => ({
      width,
      height,
      padding: [0, 0, 0, 0],
      legend: { show: false },
      cursor: { sync: { key: 'strata-s2' }, points: { show: false } },
      scales: { x: { time: false, range: () => fullRange }, y: { range: () => [0, 1] } },
      axes: [NO_X_AXIS, HIDDEN_Y_AXIS],
      series: [{}, { show: false }],
      plugins: [ribbonPlugin(() => intervalsRef.current)],
    }),
    [fullRange],
  )

  const uplotRef = useUplot(containerRef, { data, buildOptions, sync, fullRange, onRangeSettled })
  useEffect(() => {
    uplotRef.current?.setData(data)
  }, [data, uplotRef])
  useEffect(() => {
    uplotRef.current?.redraw()
  }, [ribbonIntervals, uplotRef])

  const currentState = (() => {
    if (cursorT === null) return null
    return intervals.find((iv) => iv.t0 <= cursorT && cursorT < iv.t1)?.state ?? null
  })()

  return (
    <div className="flex border-b" style={{ borderColor: 'var(--line-soft)' }}>
      <div className="flex flex-none flex-col justify-center gap-px px-3" style={{ width: GUTTER_PX }}>
        <span className="font-condensed text-label uppercase text-text-3">Rig state</span>
        <span className="font-mono text-dense" style={{ color: 'var(--ok)' }}>
          {currentState ? RIG_STATE_LABEL[currentState] : '—'}
        </span>
      </div>
      <div ref={containerRef} className="relative flex-1 my-1.5" style={{ height: RIBBON_HEIGHT_PX }} />
    </div>
  )
}
