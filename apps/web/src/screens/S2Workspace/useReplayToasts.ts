// T13.3 — toast queue state for ReplayToasts.tsx, split out so that component file only exports
// components (react-refresh/only-export-components).
import { useState } from 'react'
import type { ReplayEvent } from '../../contracts/types'

export const MAX_VISIBLE_TOASTS = 3

export type Toast = { id: string; message: string; kind: string }

export function useReplayToasts() {
  const [toasts, setToasts] = useState<Toast[]>([])

  function push(event: ReplayEvent) {
    if (event.type !== 'alert') return
    const toast: Toast = { id: `${event.alert.id}-${event.t}`, message: event.alert.message, kind: event.alert.kind }
    setToasts((prev) => [...prev, toast].slice(-MAX_VISIBLE_TOASTS))
  }

  function dismiss(id: string) {
    setToasts((prev) => prev.filter((t) => t.id !== id))
  }

  return { toasts, push, dismiss }
}
