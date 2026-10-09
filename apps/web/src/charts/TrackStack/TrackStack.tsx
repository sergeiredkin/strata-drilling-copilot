// The synchronized multi-track chart — docs/03_ARCHITECTURE.md §3.3, §3.4; comp
// S2-Workspace.dc.html. One uPlot instance per track, each row = 148px label gutter (React) +
// flex-1 canvas. Series are drawn as a min/max band + mid line so spikes survive downsampling
// (docs/04_DATA_CONTRACTS.md §4) — gaps (null buckets) are never interpolated.
import uPlot from 'uplot'
import 'uplot/dist/uPlot.min.css'
import { useEffect, useMemo, useRef } from 'react'
import type { ChannelId } from '../../contracts/types'
import { useSeriesWindow } from '../../data/hooks'
import type { DecodedSeries } from '../../data/seriesDecoder'
import { useCursor } from '../../state/cursor'
import { usePrefs } from '../../state/prefs'
import { convertValue } from '../../units/registry'
import { cursorLinePlugin } from '../plugins/cursorLine'
import { gapHatchPlugin } from '../plugins/gapHatch'
import { HIDDEN_Y_AXIS, NO_X_AXIS, TIME_X_AXIS } from './axes'
import type { TimeRangeSync } from './sync'
import { useUplot } from './useUplot'

export const GUTTER_PX = 148
export const TRACK_HEIGHT_PX = 54

export type TrackDef = {
  channel: ChannelId
  name: string
}

function toAlignedData(series: DecodedSeries | undefined): uPlot.AlignedData {
  if (!series) return [[], [], [], []]
  const n = series.t.length
  const mid = new Array<number | null>(n)
  for (let i = 0; i < n; i++) {
    const lo = series.min[i] ?? null
    const hi = series.max[i] ?? null
    mid[i] = lo === null || hi === null ? null : (lo + hi) / 2
  }
  return [series.t, series.min as (number | null)[], series.max as (number | null)[], mid]
}

function lastDefined(values: (number | null)[]): number | null {
  for (let i = values.length - 1; i >= 0; i--) {
    const v = values[i]
    if (v !== undefined && v !== null) return v
  }
  return null
}

function SensorTrack({
  track,
  unit,
  series,
  sync,
  fullRange,
  onRangeSettled,
  color,
  showCursorChip = false,
}: {
  track: TrackDef
  unit: string
  series: DecodedSeries | undefined
  sync: TimeRangeSync
  fullRange: [number, number]
  onRangeSettled: (range: [number, number]) => void
  color: string
  showCursorChip?: boolean
}) {
  const containerRef = useRef<HTMLDivElement>(null)
  const units = usePrefs((s) => s.units)
  const cursorT = useCursor((s) => s.t)
  const data = useMemo(() => toAlignedData(series), [series])

  const buildOptions = useMemo(
    () => (width: number, height: number): uPlot.Options => ({
      width,
      height,
      padding: [4, 0, 0, 0],
      legend: { show: false },
      cursor: { sync: { key: 'strata-s2' }, points: { show: false } },
      scales: { x: { time: false }, y: { auto: true } },
      axes: [NO_X_AXIS, HIDDEN_Y_AXIS],
      series: [
        {},
        { paths: () => null, points: { show: false } },
        { paths: () => null, points: { show: false } },
        { stroke: color, width: 1.4, points: { show: false }, spanGaps: false },
      ],
      bands: [{ series: [1, 2], fill: `${color}26` }],
      plugins: [gapHatchPlugin(1), cursorLinePlugin(showCursorChip)],
    }),
    [color, showCursorChip],
  )

  const uplotRef = useUplot(containerRef, { data, buildOptions, sync, fullRange, onRangeSettled })

  useEffect(() => {
    uplotRef.current?.setData(data)
  }, [data, uplotRef])

  const lastValueSi = series ? lastDefined(series.max.map((v, i) => series.min[i] ?? v)) : null
  const converted = lastValueSi === null ? null : convertValue(lastValueSi, unit as never, units)
  const cursorValueText = (() => {
    if (cursorT === null || !series) return null
    let idx = -1
    for (let i = 0; i < series.t.length; i++) {
      if (series.t[i] !== undefined && (series.t[i] as number) <= cursorT) idx = i
      else break
    }
    if (idx < 0) return null
    const v = series.max[idx] ?? series.min[idx]
    return v === null || v === undefined ? null : v
  })()

  return (
    <div className="flex border-b" style={{ borderColor: 'var(--line-soft)' }}>
      <div className="flex w-[148px] flex-none flex-col justify-center gap-px px-3 py-1.5">
        <span className="font-condensed text-label uppercase text-text-3">{track.name}</span>
        <span className="font-mono text-dense">
          {cursorValueText !== null
            ? cursorValueText.toFixed(1)
            : converted?.value !== null && converted?.value !== undefined
              ? converted.value.toFixed(1)
              : '—'}{' '}
          <span className="text-label text-text-3">{converted?.unit ?? unit}</span>
        </span>
      </div>
      <div ref={containerRef} className="relative flex-1" style={{ height: TRACK_HEIGHT_PX }} />
    </div>
  )
}

export function TrackStack({
  wellId,
  tracks,
  units: unitsByChannel,
  timeRange,
  fullRange,
  sync,
  onRangeSettled,
  plotWidthPx,
}: {
  wellId: string
  tracks: TrackDef[]
  units: Partial<Record<ChannelId, string>>
  timeRange: [number, number]
  fullRange: [number, number]
  sync: TimeRangeSync
  onRangeSettled: (range: [number, number]) => void
  plotWidthPx: number
}) {
  const channels = useMemo(() => tracks.map((t) => t.channel), [tracks])
  const seriesByChannel = useSeriesWindow(wellId, channels, timeRange[0], timeRange[1], plotWidthPx)

  const colors = ['#E9EEF3', '#9FD0FF', '#F5A524', '#6FE3C2', '#C9A7FF', '#FF9A7A', '#7CC4FF']

  return (
    <div>
      {tracks.map((track, i) => (
        <SensorTrack
          key={track.channel}
          track={track}
          unit={unitsByChannel[track.channel] ?? ''}
          series={seriesByChannel[track.channel]?.data}
          sync={sync}
          fullRange={fullRange}
          onRangeSettled={onRangeSettled}
          color={colors[i % colors.length] as string}
          showCursorChip={i === tracks.length - 1}
        />
      ))}
      <div className="flex">
        <div className="w-[148px] flex-none" />
        <div className="relative h-6 flex-1">
          <TimeAxisRow range={timeRange} />
        </div>
      </div>
    </div>
  )
}

function TimeAxisRow({ range }: { range: [number, number] }) {
  const containerRef = useRef<HTMLDivElement>(null)
  const data: uPlot.AlignedData = useMemo(() => [[range[0], range[1]], [null, null]], [range])
  const buildOptions = useMemo(
    () =>
      (width: number, height: number): uPlot.Options => ({
        width,
        height,
        padding: [0, 0, 0, 0],
        legend: { show: false },
        cursor: { show: false },
        scales: { x: { time: false, range: () => range }, y: { range: () => [0, 1] } },
        axes: [TIME_X_AXIS, { show: false }],
        series: [{}, { show: false }],
      }),
    [range],
  )
  useUplot(containerRef, { data, buildOptions, fullRange: range, interactive: false })
  return <div ref={containerRef} className="absolute inset-0" />
}
