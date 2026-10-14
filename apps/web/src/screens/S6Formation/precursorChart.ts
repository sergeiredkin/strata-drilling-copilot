// T12.3 S6 event panel — small-multiple precursor sparklines, real data in the same visual
// shape the comp (docs/design/comps/S6-Formation.dc.html) used a synthetic generator for: a
// line through `value`, a shaded band between `band_lo`/`band_hi`. Pure so it's testable without
// mounting the SVG.

export type PrecursorPaths = { line: string; band: string }

const WIDTH = 300
const HEIGHT = 48

/** `value`/`band_lo`/`band_hi` share one index -> x mapping (evenly spaced, matching how
 * `events/precursors.py` already downsamples to ~360 roughly-evenly-spaced points — this does
 * not re-derive timing from `t`, since a sparkline only needs relative position). Gaps (`null`)
 * break the line rather than interpolate across them, same rule as every other track. */
export function buildPrecursorPaths(
  value: (number | null)[],
  bandLo: (number | null)[],
  bandHi: (number | null)[],
): PrecursorPaths {
  const n = value.length
  if (n === 0) return { line: '', band: '' }

  const finite = (arr: (number | null)[]) => arr.filter((v): v is number => v !== null && Number.isFinite(v))
  const allFinite = [...finite(value), ...finite(bandLo), ...finite(bandHi)]
  if (allFinite.length === 0) return { line: '', band: '' }
  const lo = Math.min(...allFinite)
  const hi = Math.max(...allFinite)
  const span = hi - lo

  const x = (i: number) => (n > 1 ? (i / (n - 1)) * WIDTH : WIDTH / 2)
  const y = (v: number) => HEIGHT - (span > 0 ? (v - lo) / span : 0.5) * HEIGHT

  let line = ''
  let started = false
  for (let i = 0; i < n; i++) {
    const v = value[i]
    if (v === null || v === undefined || !Number.isFinite(v)) {
      started = false
      continue
    }
    line += `${started ? 'L' : 'M'}${x(i).toFixed(1)} ${y(v).toFixed(1)} `
    started = true
  }

  const top: string[] = []
  const bottom: string[] = []
  for (let i = 0; i < n; i++) {
    const hiV = bandHi[i]
    const loV = bandLo[i]
    if (
      hiV === null || hiV === undefined || loV === null || loV === undefined ||
      !Number.isFinite(hiV) || !Number.isFinite(loV)
    ) {
      continue
    }
    top.push(`${x(i).toFixed(1)} ${y(hiV).toFixed(1)}`)
    bottom.unshift(`${x(i).toFixed(1)} ${y(loV).toFixed(1)}`)
  }
  const band = top.length > 0 ? `M${top.join(' L')} L${bottom.join(' L')} Z` : ''

  return { line: line.trim(), band }
}
