// Shared uPlot axis/scale helpers so every track in the stack formats time identically.
import type uPlot from 'uplot'

export const MIN_WINDOW_MS = 2 * 60 * 1000 // zoom limit: 2 minutes ... full well (T6.1)

function pad2(n: number): string {
  return String(n).padStart(2, '0')
}

/** Compact HH:MM:SS (UTC) axis label — the full-well x-axis spans hours to weeks, so uPlot's
 * own adaptive tick spacing picks the granularity; we just need a short, consistent formatter. */
export function formatTimeTick(ms: number): string {
  const d = new Date(ms)
  return `${pad2(d.getUTCHours())}:${pad2(d.getUTCMinutes())}`
}

export function formatTimeFull(ms: number): string {
  const d = new Date(ms)
  return `${d.getUTCFullYear()}-${pad2(d.getUTCMonth() + 1)}-${pad2(d.getUTCDate())} ${pad2(d.getUTCHours())}:${pad2(d.getUTCMinutes())}:${pad2(d.getUTCSeconds())} UTC`
}

export function clampRange(
  t0: number,
  t1: number,
  fullMin: number,
  fullMax: number,
): [number, number] {
  let width = t1 - t0
  if (width < MIN_WINDOW_MS) width = MIN_WINDOW_MS
  if (width > fullMax - fullMin) width = fullMax - fullMin

  let start = t0
  if (start < fullMin) start = fullMin
  if (start + width > fullMax) start = fullMax - width
  return [start, start + width]
}

/** No visible y-axis for the sensor tracks (the gutter shows the label/unit/cursor readout in
 * React instead — docs/03_ARCHITECTURE.md §3.3) — only the x (time) axis is real. */
export const HIDDEN_Y_AXIS: uPlot.Axis = { show: false }

export const TIME_X_AXIS: uPlot.Axis = {
  stroke: 'var(--text-3)',
  grid: { stroke: 'var(--line-soft)', width: 1 },
  ticks: { stroke: 'var(--line-soft)', width: 1 },
  values: (_u, splits) => splits.map((s) => formatTimeTick(s)),
}

export const NO_X_AXIS: uPlot.Axis = { show: false }
