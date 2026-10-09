// Rig-state colour + pattern — docs/05_DESIGN_SYSTEM.md §3. Colour is never the only carrier of
// meaning (states also get distinct stripe angles/widths), and labels are drawn, not implied.
import type { RigState } from '../../contracts/types'

export const RIG_STATE_LABEL: Record<RigState, string> = {
  rotary_drilling: 'Rotary drilling',
  sliding: 'Sliding',
  connection: 'Connection',
  trip_in: 'Trip in',
  trip_out: 'Trip out',
  reaming: 'Reaming',
  circulating: 'Circulating',
  out_of_hole: 'Out of hole',
  unknown: 'Unknown',
}

export const RIG_STATE_ORDER: RigState[] = [
  'rotary_drilling',
  'sliding',
  'connection',
  'trip_in',
  'trip_out',
  'reaming',
  'circulating',
  'out_of_hole',
  'unknown',
]

type StripeSpec = { stripeVar: string; angleDeg: number; widthPx: number }

const STRIPES: Partial<Record<RigState, StripeSpec>> = {
  sliding: { stripeVar: '--state-sliding-stripe', angleDeg: 135, widthPx: 4 },
  trip_in: { stripeVar: '--state-trip-in-stripe', angleDeg: 90, widthPx: 4 },
  reaming: { stripeVar: '--state-reaming-stripe', angleDeg: 90, widthPx: 3 },
}

function cssVar(name: string, fallback: string): string {
  if (typeof window === 'undefined') return fallback
  return getComputedStyle(document.documentElement).getPropertyValue(name).trim() || fallback
}

export function rigStateFill(state: RigState): string {
  return cssVar(`--state-${state.replace(/_/g, '-')}-fill`, '#3A4552')
}

export function rigStateLabelColor(state: RigState): string {
  return cssVar(`--state-${state.replace(/_/g, '-')}-label`, '#C8D2DC')
}

const patternCache = new Map<string, CanvasPattern>()

/** Builds (and caches, per state+theme) a CanvasPattern for striped states; solid states return
 * their plain fill colour instead. Spec: "patterns built once per theme." */
export function rigStateStyle(ctx: CanvasRenderingContext2D, state: RigState): string | CanvasPattern {
  const spec = STRIPES[state]
  const fill = rigStateFill(state)
  if (!spec) return fill

  const cacheKey = `${state}:${fill}`
  const cached = patternCache.get(cacheKey)
  if (cached) return cached

  const stripeColor = cssVar(spec.stripeVar, fill)
  const size = 16
  const off = document.createElement('canvas')
  off.width = size
  off.height = size
  const octx = off.getContext('2d')
  if (!octx) return fill

  octx.fillStyle = fill
  octx.fillRect(0, 0, size, size)
  octx.strokeStyle = stripeColor
  octx.lineWidth = spec.widthPx
  const rad = (spec.angleDeg * Math.PI) / 180
  const dx = Math.cos(rad) * size * 2
  const dy = Math.sin(rad) * size * 2
  const step = spec.widthPx * 2
  for (let o = -size * 2; o < size * 2; o += step) {
    octx.beginPath()
    octx.moveTo(size / 2 + o * Math.sin(rad), size / 2 - o * Math.cos(rad) - dy)
    octx.lineTo(size / 2 + o * Math.sin(rad) + dx, size / 2 - o * Math.cos(rad) + dy)
    octx.stroke()
  }

  const pattern = ctx.createPattern(off, 'repeat')
  if (pattern) patternCache.set(cacheKey, pattern)
  return pattern ?? fill
}

export function clearPatternCache(): void {
  patternCache.clear()
}
