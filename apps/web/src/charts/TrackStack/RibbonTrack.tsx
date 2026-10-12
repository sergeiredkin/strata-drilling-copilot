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
      // uPlot calls `range(u, min, max, key)` on *every* setScale, not just the initial
      // auto-range — a callback that ignores its (min, max) args and always returns the same
      // constant silently clobbers every later u.setScale('x', ...) call back to that constant
      // (found via T10.1 e2e: the ribbon never visually reflected "Fit connection" or any zoom
      // triggered by another track — only its own drag/wheel, which calls setScale from inside
      // the same closure uPlot had already resolved). But the very first auto-range call (before
      // any series data/setScale exists) passes (min, max) as null — this track has no real
      // series data to derive bounds from (dummy 2-point data spanning fullRange, see `data`
      // above) — so that first call still needs the fullRange fallback, matching the original
      // "auto-ranging from a 2-point dummy series leaves u.scales.x.min/max as null" fix.
      scales: {
        x: { time: false, range: (_u, min, max) => (min == null || max == null ? fullRange : [min, max]) },
        y: { range: () => [0, 1] },
      },
      axes: [NO_X_AXIS, HIDDEN_Y_AXIS],
      series: [{}, { show: false }],
      plugins: [ribbonPlugin(() => intervalsRef.current)],
    }),
    [fullRange],
  )

  const uplotRef = useUplot(containerRef, { data, buildOptions, sync, fullRange, onRangeSettled })
  useEffect(() => {
    // resetScales=false: `data` is a dummy 2-point placeholder recreated on every render (new
    // `fullRange` array identity each time, since S2Workspace doesn't memoize it) — setData's
    // default resetScales=true would re-trigger the x scale's range() auto-ranging (from that
    // placeholder's own span, i.e. fullRange) on practically every render, clobbering whatever
    // zoom/pan/sync setScale() last applied. Found via T10.1 e2e: "Fit connection" visually
    // zoomed the shared x-scale correctly but the ribbon snapped back to the full well moments
    // later, right as the narrower window's rig-state refetch resolved and re-rendered this
    // component.
    uplotRef.current?.setData(data, false)
  }, [data, uplotRef])
  useEffect(() => {
    // recalcAxes=false: this plugin draws from `intervalsRef`, not uPlot's own series/scale
    // auto-ranging, so a plain redraw() (which defaults recalcAxes to true) re-invokes the x
    // scale's `range()` callback and can clobber whatever setScale() last applied (e.g. right
    // after "Fit connection" settles a narrower window and the refetched intervals arrive).
    uplotRef.current?.redraw(true, false)
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
