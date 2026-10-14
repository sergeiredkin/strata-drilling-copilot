import { describe, expect, it } from 'vitest'
import { bridgeWebSocket, replayWsUrl, type WebSocketLike } from './wsReplay'

class FakeSocket implements WebSocketLike {
  onmessage: ((ev: { data: string }) => void) | null = null
  onclose: (() => void) | null = null
  onerror: ((ev: unknown) => void) | null = null
  closed = false

  send(data: unknown): void {
    this.onmessage?.({ data: JSON.stringify(data) })
  }

  triggerClose(): void {
    this.onclose?.()
  }

  triggerError(): void {
    this.onerror?.(new Error('boom'))
  }

  close(): void {
    this.closed = true
  }
}

// `bridgeWebSocket`'s handlers register lazily, on the generator's first `.next()` pull (JS
// generator bodies don't run until pulled) -- every test below primes the generator with one
// `.next()` call before triggering anything on the fake socket, same ordering a real consumer
// gets for free (it always starts iterating immediately after creating the socket, well before
// a real network message could physically arrive).

describe('replayWsUrl', () => {
  it('rewrites http(s) to ws(s) and appends well/speed/from_t', () => {
    expect(replayWsUrl('http://localhost:8000', 'W1', 60, 1000)).toBe(
      'ws://localhost:8000/replay/W1?speed=60&from_t=1000',
    )
    expect(replayWsUrl('https://api.example.com/', 'W1', 1, 0)).toBe(
      'wss://api.example.com/replay/W1?speed=1&from_t=0',
    )
  })
})

describe('bridgeWebSocket', () => {
  it('yields messages pushed via onmessage, in order', async () => {
    const socket = new FakeSocket()
    const iter = bridgeWebSocket(socket)
    const pending1 = iter.next()
    socket.send({ type: 'state', t: 0, state: 'rotary_drilling' })
    const a = await pending1
    socket.send({ type: 'state', t: 1000, state: 'connection' })
    const b = await iter.next()
    expect(a.value?.t).toBe(0)
    expect(b.value?.t).toBe(1000)
  })

  it('ends the generator on close with no more messages', async () => {
    const socket = new FakeSocket()
    const iter = bridgeWebSocket(socket)
    const pending = iter.next()
    socket.triggerClose()
    const result = await pending
    expect(result.done).toBe(true)
  })

  it('ends the generator on error', async () => {
    const socket = new FakeSocket()
    const iter = bridgeWebSocket(socket)
    const pending = iter.next()
    socket.triggerError()
    const result = await pending
    expect(result.done).toBe(true)
  })

  it('closes the socket when the consumer stops early (return())', async () => {
    const socket = new FakeSocket()
    const iter = bridgeWebSocket(socket)
    const pending = iter.next()
    socket.send({ type: 'state', t: 0, state: 'rotary_drilling' })
    await pending
    await iter.return(undefined)
    expect(socket.closed).toBe(true)
  })

  it('drains everything already queued before reporting done', async () => {
    const socket = new FakeSocket()
    const iter = bridgeWebSocket(socket)
    const pending = iter.next()
    socket.send({ type: 'state', t: 0, state: 'rotary_drilling' })
    await pending
    socket.send({ type: 'state', t: 10, state: 'connection' })
    socket.triggerClose()
    const second = await iter.next()
    const third = await iter.next()
    expect(second.value?.t).toBe(10)
    expect(third.done).toBe(true)
  })
})
