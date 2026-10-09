// Replay transport state — docs/03_ARCHITECTURE.md §3.2. Minimal groundwork here; the actual
// timer/WS transport and S2 controls are T13.2/T13.3 (P1).
import { create } from 'zustand'
import type { ReplayEvent } from '../contracts/types'

export type ReplaySpeed = 1 | 10 | 60

type ReplayState = {
  playing: boolean
  speed: ReplaySpeed
  t: number | null
  log: ReplayEvent[]
  play: () => void
  pause: () => void
  setSpeed: (speed: ReplaySpeed) => void
  setT: (t: number | null) => void
  pushLog: (event: ReplayEvent) => void
  reset: () => void
}

export const useReplay = create<ReplayState>((set) => ({
  playing: false,
  speed: 1,
  t: null,
  log: [],
  play: () => set({ playing: true }),
  pause: () => set({ playing: false }),
  setSpeed: (speed) => set({ speed }),
  setT: (t) => set({ t }),
  pushLog: (event) => set((s) => ({ log: [...s.log, event] })),
  reset: () => set({ playing: false, t: null, log: [] }),
}))
