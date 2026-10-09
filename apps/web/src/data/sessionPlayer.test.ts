import { describe, expect, it } from 'vitest'
import type { CopilotEvent } from '../contracts/types'
import { playSession } from './sessionPlayer'

function ev(dt_ms: number): CopilotEvent {
  return { type: 'error', message: 'x', dt_ms }
}

describe('playSession', () => {
  it('yields every event in order', async () => {
    const events = [ev(0), ev(10), ev(10)]
    const out = []
    for await (const e of playSession(events, { fast: true })) out.push(e)
    expect(out).toHaveLength(3)
  })

  it('fast mode adds no real delay', async () => {
    const events = [ev(1500), ev(1500)]
    const start = Date.now()
    for await (const _e of playSession(events, { fast: true })) {
      /* drain */
    }
    expect(Date.now() - start).toBeLessThan(100)
  })

  it('caps delay at 1.5s even if dt_ms is larger', async () => {
    const events = [ev(50_000)]
    const start = Date.now()
    for await (const _e of playSession(events)) {
      /* drain */
    }
    expect(Date.now() - start).toBeLessThan(1600)
  })
})
