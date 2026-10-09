// STRS binary min/max pyramid decoder. Format: docs/04_DATA_CONTRACTS.md §4.
// Levels: docs/03_ARCHITECTURE.md §3.4 (written by pipeline/strata_pipeline/export/series.py).

const STRS_MAGIC = 0x53525453
const HEADER_BYTES = 24

export const LEVEL_BUCKET_S = [1, 8, 64, 512, 4096, 32768, 262144] as const

export type SeriesChunk = {
  t0: number
  t1: number
  bucketS: number
  n: number
  min: Float32Array
  max: Float32Array
}

export function decodeStrsBlock(buf: ArrayBuffer): SeriesChunk {
  const dv = new DataView(buf)
  const magic = dv.getUint32(0, true)
  if (magic !== STRS_MAGIC) {
    throw new Error(`bad STRS magic: 0x${magic.toString(16)}`)
  }
  const n = dv.getUint32(4, true)
  const t0 = dv.getFloat64(8, true)
  const bucketS = dv.getFloat32(16, true)
  // offset 20: reserved u32, ignored

  const min = new Float32Array(n)
  const max = new Float32Array(n)
  let offset = HEADER_BYTES
  for (let i = 0; i < n; i++) {
    min[i] = dv.getFloat32(offset, true)
    offset += 4
  }
  for (let i = 0; i < n; i++) {
    max[i] = dv.getFloat32(offset, true)
    offset += 4
  }

  return { t0, t1: t0 + n * bucketS * 1000, bucketS, n, min, max }
}

export type DecodedSeries = {
  t: Float64Array
  min: (number | null)[]
  max: (number | null)[]
}

/** NaN buckets (real gaps) become `null`, matching the "gaps are never interpolated" rule —
 * callers must never fill these in, only render them as a hatched gap. */
export function toNullableArrays(chunk: SeriesChunk): DecodedSeries {
  const t = new Float64Array(chunk.n)
  const min: (number | null)[] = new Array(chunk.n)
  const max: (number | null)[] = new Array(chunk.n)
  for (let i = 0; i < chunk.n; i++) {
    t[i] = chunk.t0 + i * chunk.bucketS * 1000
    const lo = chunk.min[i]
    const hi = chunk.max[i]
    min[i] = lo === undefined || Number.isNaN(lo) ? null : lo
    max[i] = hi === undefined || Number.isNaN(hi) ? null : hi
  }
  return { t, min, max }
}

/** Smallest level whose bucket count over [t0, t1) at `plotWidthPx` stays within the
 * ~2-buckets-per-pixel drawing budget (03_ARCHITECTURE.md §3.4). */
export function chooseLevel(t0Ms: number, t1Ms: number, plotWidthPx: number): number {
  const spanS = (t1Ms - t0Ms) / 1000
  for (let level = 0; level < LEVEL_BUCKET_S.length; level++) {
    const bucketS = LEVEL_BUCKET_S[level] as number
    if (spanS / bucketS <= 2 * plotWidthPx) return level
  }
  return LEVEL_BUCKET_S.length - 1
}
