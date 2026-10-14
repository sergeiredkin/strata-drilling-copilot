import { describe, expect, it } from 'vitest'
import type { ReplayEvent } from '../contracts/types'
import { playReplay } from './replayPlayer'

function stateEvent(t: number): ReplayEvent {
  return { type: 'state', t, state: 'rotary_drilling' }
}

describe('playReplay', () => {
  it('yields every event in order', async () => {
    const events = [stateEvent(0), stateEvent(1000), stateEvent(2000)]
    const out = []
    for await (const e of playReplay(events, { fast: true })) out.push(e)
    expect(out).toHaveLength(3)
  })

  it('fast mode adds no real delay', async () => {
    const events = [stateEvent(0), stateEvent(60_000)]
    const start = Date.now()
    for await (const _e of playReplay(events, { fast: true })) {
      /* drain */
    }
    expect(Date.now() - start).toBeLessThan(100)
  })

  it('caps delay at 1.5s even for a long real gap', async () => {
    const events = [stateEvent(0), stateEvent(3_600_000)] // 1h real gap
    const start = Date.now()
    for await (const _e of playReplay(events, { speed: 1 })) {
      /* drain */
    }
    expect(Date.now() - start).toBeLessThan(1700)
  })

  it('a higher speed shortens the real delay between events', async () => {
    const events = [stateEvent(0), stateEvent(1000)] // 1s real gap
    const start = Date.now()
    for await (const _e of playReplay(events, { speed: 60 })) {
      /* drain */
    }
    // 1000ms / 60 ~= 16.7ms -- comfortably under the uncapped 1s it'd take at speed 1
    expect(Date.now() - start).toBeLessThan(200)
  })

  it('accepts an async iterable, not just an array', async () => {
    async function* gen(): AsyncGenerator<ReplayEvent> {
      yield stateEvent(0)
      yield stateEvent(10)
    }
    const out = []
    for await (const e of playReplay(gen(), { fast: true })) out.push(e)
    expect(out).toHaveLength(2)
  })
})
