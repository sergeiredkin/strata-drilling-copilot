// DDR lane row + mismatch ▲ markers — comp S2-Workspace.dc.html ("Daily report" / "DDR op codes").
import uPlot from 'uplot'
import { useEffect, useMemo, useRef } from 'react'
import type { DdrActivity, Mismatch } from '../../contracts/types'
import { ddrLanePlugin, type DdrLaneRow } from '../plugins/ddrLane'
import { mismatchPlugin, type MismatchMarker } from '../plugins/mismatch'
import { HIDDEN_Y_AXIS, NO_X_AXIS } from './axes'
import type { TimeRangeSync } from './sync'
import { GUTTER_PX } from './TrackStack'
import { useUplot } from './useUplot'

export const DDR_LANE_HEIGHT_PX = 36

export function DdrLaneTrack({
  rows,
  mismatches,
  fullRange,
  sync,
  onRangeSettled,
  onMismatchClick,
}: {
  rows: DdrActivity[]
  mismatches: Mismatch[]
  fullRange: [number, number]
  sync: TimeRangeSync
  onRangeSettled: (range: [number, number]) => void
  onMismatchClick: (mismatchId: string) => void
}) {
  const containerRef = useRef<HTMLDivElement>(null)

  const ddrRows: DdrLaneRow[] = useMemo(
    () => rows.map((r) => ({ t0: r.t0, t1: r.t1, code: r.code, narrative: r.narrative })),
    [rows],
  )
  const markers: MismatchMarker[] = useMemo(
    () => mismatches.map((m) => ({ id: m.id, t0: m.t0, t1: m.t1 })),
    [mismatches],
  )

  // See RibbonTrack.tsx for why these are refs read by the plugin, not direct closures: the
  // uPlot instance (and its plugins) is constructed once and never remounted on prop changes.
  const rowsRef = useRef(ddrRows)
  rowsRef.current = ddrRows
  const markersRef = useRef(markers)
  markersRef.current = markers
  const onMismatchClickRef = useRef(onMismatchClick)
  onMismatchClickRef.current = onMismatchClick

  const data: uPlot.AlignedData = useMemo(() => [fullRange, [null, null]], [fullRange])

  const buildOptions = useMemo(
    () => (width: number, height: number): uPlot.Options => ({
      width,
      height,
      padding: [12, 0, 0, 0],
      legend: { show: false },
      cursor: { sync: { key: 'strata-s2' }, points: { show: false } },
      scales: { x: { time: false, range: () => fullRange }, y: { range: () => [0, 1] } },
      axes: [NO_X_AXIS, HIDDEN_Y_AXIS],
      series: [{}, { show: false }],
      plugins: [
        ddrLanePlugin(() => rowsRef.current),
        mismatchPlugin(
          () => markersRef.current,
          (id) => onMismatchClickRef.current(id),
        ),
      ],
    }),
    [fullRange],
  )

  const uplotRef = useUplot(containerRef, { data, buildOptions, sync, fullRange, onRangeSettled })
  useEffect(() => {
    uplotRef.current?.setData(data)
  }, [data, uplotRef])
  useEffect(() => {
    uplotRef.current?.redraw()
  }, [ddrRows, markers, uplotRef])

  return (
    <div className="flex border-b" style={{ borderColor: 'var(--line-soft)' }}>
      <div className="flex flex-none flex-col justify-center gap-px px-3" style={{ width: GUTTER_PX }}>
        <span className="font-condensed text-label uppercase text-text-3">Daily report</span>
        <span className="font-mono text-meta text-text-3">DDR op codes</span>
      </div>
      <div ref={containerRef} className="relative flex-1 my-1.5" style={{ height: DDR_LANE_HEIGHT_PX }} />
    </div>
  )
}
