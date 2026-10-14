import { describe, expect, it } from 'vitest'
import { buildPrecursorPaths } from './precursorChart'

describe('buildPrecursorPaths', () => {
  it('returns empty paths for an empty series', () => {
    expect(buildPrecursorPaths([], [], [])).toEqual({ line: '', band: '' })
  })

  it('returns empty paths when nothing is finite', () => {
    expect(buildPrecursorPaths([null, null], [null, null], [null, null])).toEqual({ line: '', band: '' })
  })

  it('draws a continuous line through finite values', () => {
    const { line } = buildPrecursorPaths([10, 20, 30], [5, 5, 5], [35, 35, 35])
    expect(line.startsWith('M')).toBe(true)
    expect(line).toContain('L')
  })

  it('breaks the line at a gap rather than interpolating across it', () => {
    const { line } = buildPrecursorPaths([10, null, 30], [5, 5, 5], [35, 35, 35])
    const segments = line.split('M').filter(Boolean)
    expect(segments.length).toBe(2)
  })

  it('builds a closed band polygon from band_lo/band_hi', () => {
    const { band } = buildPrecursorPaths([20, 20, 20], [10, 10, 10], [30, 30, 30])
    expect(band.startsWith('M')).toBe(true)
    expect(band.endsWith('Z')).toBe(true)
  })

  it('omits the band when band_lo/band_hi are null (no same-well samples to form one)', () => {
    const { band } = buildPrecursorPaths([20, 20, 20], [null, null, null], [null, null, null])
    expect(band).toBe('')
  })
})
