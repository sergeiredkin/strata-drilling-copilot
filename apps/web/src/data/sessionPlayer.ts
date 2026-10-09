// Replays a recorded copilot session's events honouring their recorded `dt_ms`, capped at
// 1.5 s per step (docs/03_ARCHITECTURE.md §3.1). `fast` (the `?fast=1` URL param) collapses
// every delay to 0, for tests and the Playwright demo script.
import type { CopilotEvent } from '../contracts/types'

const MAX_DELAY_MS = 1500

function sleep(ms: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms))
}

export async function* playSession(
  events: CopilotEvent[],
  opts: { fast?: boolean } = {},
): AsyncGenerator<CopilotEvent, void, unknown> {
  for (const event of events) {
    const delay = opts.fast ? 0 : Math.min(event.dt_ms, MAX_DELAY_MS)
    if (delay > 0) {
      await sleep(delay)
    }
    yield event
  }
}

export function isFastMode(): boolean {
  if (typeof window === 'undefined') return false
  return new URLSearchParams(window.location.search).get('fast') === '1'
}
