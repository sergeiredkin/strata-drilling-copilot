// T13.3 — drives `useReplay`'s playing/t/log state from a `DataSource.replay()` stream: advances
// the replay head, keeps the track window on the last 30 min following it (06 S8), and routes
// alert events out to the caller (for toasts) while logging them in the store (for the event
// log drawer). State transitions are NOT logged — 06 S8 only calls for alerts in the log; a
// per-state-change entry would make the drawer unusable on a long well.
import { useCallback, useRef } from 'react'
import type { ReplayEvent } from '../../contracts/types'
import { clampRange } from '../../charts/TrackStack/axes'
import type { TimeRangeSync } from '../../charts/TrackStack/sync'
import { getDataSource } from '../../data/createDataSource'
import { useReplay } from '../../state/replay'

const REPLAY_WINDOW_MS = 30 * 60_000

export function useReplayRunner(
  wellId: string | undefined,
  fullRange: [number, number] | null,
  sync: TimeRangeSync,
  onRangeSettled: (range: [number, number]) => void,
  onAlert: (alert: ReplayEvent) => void,
) {
  const tokenRef = useRef<{ cancelled: boolean } | null>(null)

  const stop = useCallback(() => {
    if (tokenRef.current) tokenRef.current.cancelled = true
    useReplay.getState().pause()
  }, [])

  const start = useCallback(
    (fromT: number) => {
      if (!wellId || !fullRange) return
      stop() // cancel any run already in flight before starting a new one
      const token = { cancelled: false }
      tokenRef.current = token
      useReplay.getState().setT(fromT)
      useReplay.getState().play()

      void (async () => {
        const ds = getDataSource()
        const speed = useReplay.getState().speed
        for await (const event of ds.replay(wellId, speed, fromT)) {
          if (token.cancelled) return
          useReplay.getState().setT(event.t)
          const next = clampRange(event.t - REPLAY_WINDOW_MS, event.t, fullRange[0], fullRange[1])
          sync.setRange(next)
          onRangeSettled(next)
          if (event.type === 'alert') {
            useReplay.getState().pushLog(event)
            onAlert(event)
          }
        }
        if (!token.cancelled) useReplay.getState().pause()
      })()
    },
    [wellId, fullRange, sync, onRangeSettled, onAlert, stop],
  )

  return { start, stop }
}
