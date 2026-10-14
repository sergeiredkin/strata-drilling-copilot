// T13.2 replay timing — mirrors sessionPlayer.ts's delay-capping convention, generalised to
// accept a `speed` multiplier (1x/10x/60x, docs/06_SCREENS.md S8) on top of the real elapsed
// time between two events' timestamps. Pure: takes an already-time-ordered stream of events
// (sync or async) and only adds delays, so it's testable with fake timers without any fetch.
import type { ChannelId, ReplayEvent, SeriesIndex } from '../contracts/types'
import { toNullableArrays, type SeriesChunk } from './seriesDecoder'

const MAX_DELAY_MS = 1500

function sleep(ms: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms))
}

type ChunkMeta = SeriesIndex['channels'][string]['levels'][number]['chunks'][number]

/** Lazily merges `stateAlerts` (already filtered to `t >= fromT` and time-sorted by the caller)
 * with `sample` events decoded one L0 chunk at a time via `fetchChunk` — decodes and discards
 * each chunk's arrays before moving to the next, so a long well's full replay never holds more
 * than one chunk's worth of samples per channel in memory. */
export async function* mergeReplayEvents(
  index: SeriesIndex,
  channels: ChannelId[],
  chunkMetas: ChunkMeta[],
  stateAlerts: ReplayEvent[],
  fromT: number,
  fetchChunk: (ch: ChannelId, chunkIndex: number) => Promise<SeriesChunk>,
): AsyncGenerator<ReplayEvent, void, unknown> {
  let saIdx = 0

  for (const chunkMeta of chunkMetas) {
    const decoded = await Promise.all(
      channels.map(async (ch) => {
        const chChunk = index.channels[ch]?.levels.find((l) => l.level === 0)?.chunks.find((c) => c.t0 === chunkMeta.t0)
        return chChunk ? toNullableArrays(await fetchChunk(ch, chChunk.i)) : null
      }),
    )
    const first = decoded.find((d) => d !== null)
    const n = first?.t.length ?? 0
    for (let i = 0; i < n; i++) {
      const t = first?.t[i]
      if (t === undefined || t < fromT) continue
      while (saIdx < stateAlerts.length) {
        const next = stateAlerts[saIdx]
        if (!next || next.t > t) break
        yield next
        saIdx++
      }
      const values: Record<string, number | null> = {}
      channels.forEach((ch, idx) => {
        values[ch] = decoded[idx]?.min[i] ?? null
      })
      yield { type: 'sample', t, values }
    }
  }

  while (saIdx < stateAlerts.length) {
    const next = stateAlerts[saIdx]
    if (!next) break
    yield next
    saIdx++
  }
}

export async function* playReplay(
  events: Iterable<ReplayEvent> | AsyncIterable<ReplayEvent>,
  opts: { speed?: 1 | 10 | 60; fast?: boolean } = {},
): AsyncGenerator<ReplayEvent, void, unknown> {
  const speed = opts.speed ?? 1
  let lastT: number | null = null
  for await (const event of events) {
    if (!opts.fast && lastT !== null) {
      const delay = Math.min((event.t - lastT) / speed, MAX_DELAY_MS)
      if (delay > 0) await sleep(delay)
    }
    lastT = event.t
    yield event
  }
}
