// Cursor time position — docs/03_ARCHITECTURE.md §3.2. Never in the URL; updated through rAF by
// chart interactions (T6.x), consumed by uPlot cursor.sync and track readouts.
import { create } from 'zustand'

type CursorState = {
  t: number | null
  setT: (t: number | null) => void
}

export const useCursor = create<CursorState>((set) => ({
  t: null,
  setT: (t) => set({ t }),
}))
