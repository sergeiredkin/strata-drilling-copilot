import { describe, expect, it } from 'vitest'
import type { ChannelId, ReplayEvent, SeriesIndex } from '../contracts/types'
import { mergeReplayEvents } from './replayPlayer'
import type { SeriesChunk } from './seriesDecoder'

function chunk(t0: number, values: number[]): SeriesChunk {
  const arr = new Float32Array(values)
  return { t0, t1: t0 + values.length * 1000, bucketS: 1, n: values.length, min: arr, max: arr }
}

function seriesIndexFor(channels: ChannelId[], t0: number, n: number): SeriesIndex {
  const idx: SeriesIndex = { well: 'W1', channels: {} }
  for (const ch of channels) {
    idx.channels[ch] = {
      unit: '1', source: 'test', gaps: [],
      levels: [{ level: 0, bucket_s: 1, chunks: [{ i: 0, t0, t1: t0 + n * 1000, n, file: 'x.bin' }] }],
    }
  }
  return idx
}

function stateEvent(t: number): ReplayEvent {
  return { type: 'state', t, state: 'rotary_drilling' }
}

function chunksFor(index: SeriesIndex, ch: ChannelId) {
  const level0 = index.channels[ch]?.levels.find((l) => l.level === 0)
  if (!level0) throw new Error(`no L0 level for channel ${ch} in test fixture`)
  return level0.chunks
}

describe('mergeReplayEvents', () => {
  it('decodes sample events from the chunk fetcher and interleaves state/alert events by time', async () => {
    const index = seriesIndexFor(['HKLD'], 0, 3)
    const chunkMetas = chunksFor(index, 'HKLD')
    const stateAlerts = [stateEvent(500)]
    const fetchChunk = async () => chunk(0, [10, 20, 30])

    const out: ReplayEvent[] = []
    for await (const e of mergeReplayEvents(index, ['HKLD'], chunkMetas, stateAlerts, 0, fetchChunk)) {
      out.push(e)
    }
    // samples at t=0,1000,2000 plus the state event at t=500, in time order.
    expect(out.map((e) => e.t)).toEqual([0, 500, 1000, 2000])
    expect(out[1]?.type).toBe('state')
    const sample0 = out[0]
    if (sample0?.type !== 'sample') throw new Error('expected a sample event')
    expect(sample0.values.HKLD).toBe(10)
  })

  it('filters out samples before fromT', async () => {
    const index = seriesIndexFor(['HKLD'], 0, 3)
    const chunkMetas = chunksFor(index, 'HKLD')
    const fetchChunk = async () => chunk(0, [10, 20, 30])

    const out: ReplayEvent[] = []
    for await (const e of mergeReplayEvents(index, ['HKLD'], chunkMetas, [], 1500, fetchChunk)) out.push(e)
    expect(out.map((e) => e.t)).toEqual([2000])
  })

  it('merges multiple channels into one sample event per timestamp', async () => {
    const index = seriesIndexFor(['HKLD', 'TORQ'], 0, 2)
    const chunkMetas = chunksFor(index, 'HKLD')
    const fetchChunk = async (ch: ChannelId) => (ch === 'HKLD' ? chunk(0, [10, 20]) : chunk(0, [1, 2]))

    const out: ReplayEvent[] = []
    for await (const e of mergeReplayEvents(index, ['HKLD', 'TORQ'], chunkMetas, [], 0, fetchChunk)) out.push(e)
    const first = out[0]
    if (first?.type !== 'sample') throw new Error('expected a sample event')
    expect(first.values).toEqual({ HKLD: 10, TORQ: 1 })
  })

  it('drains remaining state/alert events after the last chunk', async () => {
    const index = seriesIndexFor(['HKLD'], 0, 1)
    const chunkMetas = chunksFor(index, 'HKLD')
    const stateAlerts = [stateEvent(5000)] // well after the only sample at t=0
    const fetchChunk = async () => chunk(0, [10])

    const out: ReplayEvent[] = []
    for await (const e of mergeReplayEvents(index, ['HKLD'], chunkMetas, stateAlerts, 0, fetchChunk)) out.push(e)
    expect(out.map((e) => e.t)).toEqual([0, 5000])
  })

  it('yields only state/alert events when there are no chunks at all', async () => {
    const index = seriesIndexFor([], 0, 0)
    const stateAlerts = [stateEvent(0), stateEvent(10)]
    const out: ReplayEvent[] = []
    for await (const e of mergeReplayEvents(index, [], [], stateAlerts, 0, async () => chunk(0, []))) out.push(e)
    expect(out).toHaveLength(2)
  })
})
