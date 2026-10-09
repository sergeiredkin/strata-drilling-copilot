import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'
import { describe, expect, it } from 'vitest'
import { chooseLevel, decodeStrsBlock, LEVEL_BUCKET_S, toNullableArrays } from './seriesDecoder'

// Fixture written by pipeline/strata_pipeline/export/series.py (write_strs) — see T1.3 summary
// for the exact generating snippet. Values: mins=[1,2,3,NaN,5,999], maxs=[1.5,2.5,3.5,NaN,5.5,999.5],
// t0=1_700_000_000_000 ms, bucket_s=8.
const FIXTURE_PATH = resolve(process.cwd(), 'src/data/__fixtures__/strs_sample.bin')

describe('decodeStrsBlock (round-trip with the Python writer)', () => {
  const buf = readFileSync(FIXTURE_PATH)
  const chunk = decodeStrsBlock(buf.buffer.slice(buf.byteOffset, buf.byteOffset + buf.byteLength))

  it('decodes header fields', () => {
    expect(chunk.n).toBe(6)
    expect(chunk.t0).toBe(1_700_000_000_000)
    expect(chunk.bucketS).toBe(8)
    expect(chunk.t1).toBe(1_700_000_000_000 + 6 * 8 * 1000)
  })

  it('decodes min/max arrays, preserving the spike', () => {
    expect(Array.from(chunk.min)).toEqual([1, 2, 3, NaN, 5, 999])
    expect(Array.from(chunk.max)).toEqual([1.5, 2.5, 3.5, NaN, 5.5, 999.5])
  })

  it('maps NaN buckets to null, not interpolated values', () => {
    const { t, min, max } = toNullableArrays(chunk)
    expect(min[3]).toBeNull()
    expect(max[3]).toBeNull()
    expect(min[5]).toBe(999)
    expect(t[0]).toBe(1_700_000_000_000)
    expect(t[1]).toBe(1_700_000_000_000 + 8000)
  })

  it('throws on a bad magic', () => {
    const bad = new ArrayBuffer(24)
    expect(() => decodeStrsBlock(bad)).toThrow(/bad STRS magic/)
  })
})

describe('chooseLevel', () => {
  it('picks L0 for a short window', () => {
    expect(chooseLevel(0, 60_000, 1000)).toBe(0) // 60 buckets over 2000px budget
  })

  it('picks a coarser level as the window widens', () => {
    const oneDayMs = 24 * 3600 * 1000
    const level = chooseLevel(0, 30 * oneDayMs, 1200)
    expect(level).toBeGreaterThan(0)
    expect(level).toBeLessThan(LEVEL_BUCKET_S.length)
  })

  it('falls back to the coarsest level for a huge window', () => {
    expect(chooseLevel(0, 1000 * 365 * 24 * 3600 * 1000, 100)).toBe(LEVEL_BUCKET_S.length - 1)
  })
})
