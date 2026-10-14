import { describe, expect, it } from 'vitest'
import { mdIntervalToTimeWindow } from './depthTimeLink'

const DEPTH_TIME = {
  t: [1000, 1060, 1120, 1180, 1240],
  bit_md: [2000, 2010, 2020, 2030, 2040],
  hole_md: [2000, 2010, 2020, 2030, 2040],
}

describe('mdIntervalToTimeWindow', () => {
  it('returns the time span of every sample whose BITDEPTH falls in [mdTop, mdBase)', () => {
    expect(mdIntervalToTimeWindow(DEPTH_TIME, 2010, 2030)).toEqual({ t0: 1060, t1: 1120 })
  })

  it('treats md_base as exclusive', () => {
    const window = mdIntervalToTimeWindow(DEPTH_TIME, 2000, 2020)
    expect(window).toEqual({ t0: 1000, t1: 1060 })
  })

  it('returns null when no sample ever falls in the requested range', () => {
    expect(mdIntervalToTimeWindow(DEPTH_TIME, 9000, 9100)).toBeNull()
  })

  it('skips null/missing BITDEPTH samples rather than treating them as a match', () => {
    const withGap = { ...DEPTH_TIME, bit_md: [2000, null, 2020, 2030, 2040] }
    expect(mdIntervalToTimeWindow(withGap, 2000, 2020)).toEqual({ t0: 1000, t1: 1000 })
  })
})
