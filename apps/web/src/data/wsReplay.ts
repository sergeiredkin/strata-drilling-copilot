// T13.2 live replay transport — bridges a WebSocket's push-based `onmessage`/`onclose`/`onerror`
// callbacks into a pull-based `AsyncGenerator<ReplayEvent>`, the same shape `StaticSource.replay`
// already returns, so `useReplay` (T13.3) can consume either source identically ("same reducer
// for static and live", docs/03_ARCHITECTURE.md §4). Takes a minimal structural type instead of
// the real `WebSocket` so it's testable with a plain fake, no server or jsdom WS support needed.
import type { ReplayEvent } from '../contracts/types'

export type WebSocketLike = {
  onmessage: ((ev: { data: string }) => void) | null
  onclose: (() => void) | null
  onerror: ((ev: unknown) => void) | null
  close(): void
}

export function replayWsUrl(apiBaseUrl: string, wellId: string, speed: 1 | 10 | 60, fromT: number): string {
  const wsBase = apiBaseUrl.replace(/^http/, 'ws').replace(/\/$/, '')
  return `${wsBase}/replay/${wellId}?speed=${speed}&from_t=${fromT}`
}

export async function* bridgeWebSocket(socket: WebSocketLike): AsyncGenerator<ReplayEvent, void, unknown> {
  const queue: ReplayEvent[] = []
  let done = false
  let wake: (() => void) | null = null

  socket.onmessage = (ev) => {
    queue.push(JSON.parse(ev.data) as ReplayEvent)
    wake?.()
  }
  socket.onclose = () => {
    done = true
    wake?.()
  }
  socket.onerror = () => {
    done = true
    wake?.()
  }

  try {
    while (true) {
      while (queue.length > 0) {
        yield queue.shift() as ReplayEvent
      }
      if (done) return
      await new Promise<void>((resolve) => {
        wake = resolve
      })
      wake = null
    }
  } finally {
    socket.close()
  }
}
