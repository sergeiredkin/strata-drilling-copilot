// Pure MD<->pixel mapping for S6's depth grid, same linear scale the comp
// (docs/design/comps/S6-Formation.dc.html) uses — no charting library involved, since every
// track here is either an absolutely-positioned colour band or a hand-built SVG path.

export function mdToY(md: number, mdMin: number, mdMax: number, heightPx: number): number {
  if (mdMax <= mdMin) return 0
  return ((md - mdMin) / (mdMax - mdMin)) * heightPx
}

export type DepthTick = { label: string; y: number }

export function buildDepthTicks(mdMin: number, mdMax: number, heightPx: number, step = 100): DepthTick[] {
  const ticks: DepthTick[] = []
  const start = Math.ceil(mdMin / step) * step
  for (let d = start; d <= mdMax; d += step) {
    ticks.push({
      label: Math.round(d).toLocaleString('en-US'),
      y: Math.min(mdToY(d, mdMin, mdMax, heightPx), heightPx - 14),
    })
  }
  return ticks
}

/** One SVG path (viewBox `0 0 100 heightPx`-ish, x in [0,100]) through every finite value,
 * breaking (not interpolating) across gaps — a `null` restarts the path rather than connecting
 * across it, same "gaps are never interpolated" rule as the time-indexed tracks. */
export function buildCurvePath(
  md: number[],
  values: (number | null)[],
  mdMin: number,
  mdMax: number,
  heightPx: number,
  valueMin: number,
  valueMax: number,
  leftMargin = 8,
  rightMargin = 8,
): string {
  let path = ''
  let started = false
  const span = valueMax - valueMin
  for (let i = 0; i < md.length; i++) {
    const v = values[i]
    if (v === null || !Number.isFinite(v)) {
      started = false
      continue
    }
    const frac = span > 0 ? (v - valueMin) / span : 0.5
    const x = leftMargin + Math.max(0, Math.min(1, frac)) * (100 - leftMargin - rightMargin)
    const y = mdToY(md[i], mdMin, mdMax, heightPx)
    path += `${started ? 'L' : 'M'}${x.toFixed(1)} ${y.toFixed(1)} `
    started = true
  }
  return path.trim()
}

export function finiteRange(values: (number | null)[]): [number, number] | null {
  const finite = values.filter((v): v is number => v !== null && Number.isFinite(v))
  if (finite.length === 0) return null
  return [Math.min(...finite), Math.max(...finite)]
}

// A small, stable palette so any formation name (real or mock/FORGE) gets a consistent, visually
// distinct colour without hand-mapping every possible name.
const PALETTE = [
  '#A7C4A0', '#D9C27A', '#8F8F8F', '#B0A08A', '#E8D27A', '#C9A97A', '#C98A6A', '#7F9CB0',
  '#C9B27A', '#5D6D7E', '#9FB8A0', '#D8B4D8',
]

export function colorForFormation(name: string): string {
  let hash = 0
  for (let i = 0; i < name.length; i++) hash = (hash * 31 + name.charCodeAt(i)) >>> 0
  return PALETTE[hash % PALETTE.length]
}
