import { describe, expect, it } from 'vitest'
import { buildCurvePath, buildDepthTicks, colorForFormation, finiteRange, mdToY } from './depthScale'

describe('mdToY', () => {
  it('maps the MD range linearly onto [0, heightPx]', () => {
    expect(mdToY(1000, 1000, 2000, 720)).toBe(0)
    expect(mdToY(2000, 1000, 2000, 720)).toBe(720)
    expect(mdToY(1500, 1000, 2000, 720)).toBe(360)
  })

  it('returns 0 for a degenerate range rather than dividing by zero', () => {
    expect(mdToY(1000, 1000, 1000, 720)).toBe(0)
  })
})

describe('buildDepthTicks', () => {
  it('produces evenly spaced ticks within the range, clamped near the bottom edge', () => {
    const ticks = buildDepthTicks(1000, 1300, 720, 100)
    expect(ticks.map((t) => t.label)).toEqual(['1,000', '1,100', '1,200', '1,300'])
    expect(ticks[ticks.length - 1]?.y).toBeLessThanOrEqual(720 - 14)
  })
})

describe('buildCurvePath', () => {
  it('draws a continuous path through finite values', () => {
    const path = buildCurvePath([0, 1, 2], [10, 20, 30], 0, 2, 100, 10, 30)
    expect(path.startsWith('M')).toBe(true)
    expect(path).toContain('L')
  })

  it('breaks the path at a null (gap), never interpolating across it', () => {
    const path = buildCurvePath([0, 1, 2], [10, null, 30], 0, 2, 100, 10, 30)
    const segments = path.split('M').filter(Boolean)
    expect(segments.length).toBe(2) // two disjoint M-started segments, not one continuous L
  })

  it('returns an empty path when every value is null', () => {
    expect(buildCurvePath([0, 1], [null, null], 0, 1, 100, 0, 1)).toBe('')
  })
})

describe('finiteRange', () => {
  it('ignores nulls when computing min/max', () => {
    expect(finiteRange([1, null, 5, 3])).toEqual([1, 5])
  })

  it('returns null when nothing is finite', () => {
    expect(finiteRange([null, null])).toBeNull()
  })
})

describe('colorForFormation', () => {
  it('is deterministic for the same name', () => {
    expect(colorForFormation('Hugin Fm. VOLVE')).toBe(colorForFormation('Hugin Fm. VOLVE'))
  })

  it('returns a valid hex colour', () => {
    expect(colorForFormation('Some Formation')).toMatch(/^#[0-9A-Fa-f]{6}$/)
  })
})
