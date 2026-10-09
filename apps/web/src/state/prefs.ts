// Persisted user prefs — docs/03_ARCHITECTURE.md §3.2. localStorage only, never the URL; every
// access is try/catch'd since storage can throw (private mode, quota, disabled cookies).
import { create } from 'zustand'

export type UnitSystem = 'metric' | 'oilfield'
export type ThemeName = 'dark' | 'light'

const STORAGE_KEY = 'strata.prefs.v1'

type PersistedPrefs = { units: UnitSystem; theme: ThemeName }

const DEFAULTS: PersistedPrefs = { units: 'metric', theme: 'dark' }

function readPersisted(): PersistedPrefs {
  try {
    const raw = window.localStorage.getItem(STORAGE_KEY)
    if (!raw) return DEFAULTS
    const parsed = JSON.parse(raw) as Partial<PersistedPrefs>
    return {
      units: parsed.units === 'oilfield' ? 'oilfield' : 'metric',
      theme: parsed.theme === 'light' ? 'light' : 'dark',
    }
  } catch {
    return DEFAULTS
  }
}

function writePersisted(prefs: PersistedPrefs): void {
  try {
    window.localStorage.setItem(STORAGE_KEY, JSON.stringify(prefs))
  } catch {
    // storage unavailable — prefs just won't survive reload this session.
  }
}

type PrefsState = PersistedPrefs & {
  setUnits: (units: UnitSystem) => void
  toggleUnits: () => void
  setTheme: (theme: ThemeName) => void
  toggleTheme: () => void
}

export const usePrefs = create<PrefsState>((set, get) => ({
  ...readPersisted(),
  setUnits: (units) => {
    set({ units })
    writePersisted({ units, theme: get().theme })
  },
  toggleUnits: () => {
    const units = get().units === 'metric' ? 'oilfield' : 'metric'
    set({ units })
    writePersisted({ units, theme: get().theme })
  },
  setTheme: (theme) => {
    set({ theme })
    writePersisted({ units: get().units, theme })
  },
  toggleTheme: () => {
    const theme = get().theme === 'dark' ? 'light' : 'dark'
    set({ theme })
    writePersisted({ units: get().units, theme })
  },
}))
