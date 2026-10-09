// Cross-track time-range sync — docs/03_ARCHITECTURE.md §3.3 ("shared x-scale set via setScale
// broadcast"). A plain pub-sub, not React state: during an active wheel/drag interaction every
// track calls `setRange` many times a frame, and nothing here should trigger a React re-render —
// each TrackStack instance applies the new range to its own uPlot instance imperatively via
// `u.setScale()`. `useView.setTimeRange` (the URL-persisted range) is only written once the
// interaction settles, by the caller, not by this module.
export type TimeRange = [number, number]
type Listener = (range: TimeRange, origin: symbol | undefined) => void

class TimeRangeSync {
  private range: TimeRange | null = null
  private listeners = new Set<Listener>()

  getRange(): TimeRange | null {
    return this.range
  }

  /** `origin` identifies the track that originated the change, so that track can skip re-
   * applying a scale it already has (avoids feedback loops / redundant uPlot.setScale calls). */
  setRange(range: TimeRange, origin?: symbol): void {
    this.range = range
    for (const listener of this.listeners) listener(range, origin)
  }

  subscribe(listener: Listener): () => void {
    this.listeners.add(listener)
    return () => this.listeners.delete(listener)
  }
}

/** One sync instance per mounted S2 workspace (created by the screen, passed down via props/
 * context) — not a module-level singleton, so multiple instances (tests, future split views)
 * never cross-talk. */
export function createTimeRangeSync(initial: TimeRange): TimeRangeSync {
  const sync = new TimeRangeSync()
  sync.setRange(initial)
  return sync
}

export type { TimeRangeSync }
