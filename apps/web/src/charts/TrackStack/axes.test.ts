import { describe, expect, it } from 'vitest'
import { clampRange, MIN_WINDOW_MS } from './axes'

describe('clampRange', () => {
  const fullMin = 0
  const fullMax = 1_000_000

  it('passes through a range already within bounds and above the minimum width', () => {
    expect(clampRange(100_000, 300_000, fullMin, fullMax)).toEqual([100_000, 300_000])
  })

  it('clamps a window narrower than MIN_WINDOW_MS up to the minimum, keeping its start', () => {
    const [t0, t1] = clampRange(100_000, 100_100, fullMin, fullMax)
    expect(t1 - t0).toBe(MIN_WINDOW_MS)
    expect(t0).toBe(100_000)
  })

  it('clamps a window wider than the full well down to the full well', () => {
    expect(clampRange(-500_000, 1_500_000, fullMin, fullMax)).toEqual([fullMin, fullMax])
  })

  it('shifts a window that starts before fullMin back into bounds', () => {
    expect(clampRange(-50_000, 150_000, fullMin, fullMax)).toEqual([0, 200_000])
  })

  it('shifts a window that ends after fullMax back into bounds', () => {
    const [t0, t1] = clampRange(900_000, 1_100_000, fullMin, fullMax)
    expect(t1).toBe(fullMax)
    expect(t1 - t0).toBe(200_000)
  })
})
