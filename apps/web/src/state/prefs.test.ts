import { beforeEach, describe, expect, it, vi } from 'vitest'
import { usePrefs } from './prefs'

describe('usePrefs', () => {
  beforeEach(() => {
    window.localStorage.clear()
    usePrefs.setState({ units: 'metric', theme: 'dark' })
  })

  it('defaults to metric/dark', () => {
    expect(usePrefs.getState().units).toBe('metric')
    expect(usePrefs.getState().theme).toBe('dark')
  })

  it('toggleUnits flips and persists to localStorage', () => {
    usePrefs.getState().toggleUnits()
    expect(usePrefs.getState().units).toBe('oilfield')
    const stored = JSON.parse(window.localStorage.getItem('strata.prefs.v1') ?? '{}')
    expect(stored.units).toBe('oilfield')

    usePrefs.getState().toggleUnits()
    expect(usePrefs.getState().units).toBe('metric')
  })

  it('toggleTheme flips and persists', () => {
    usePrefs.getState().toggleTheme()
    expect(usePrefs.getState().theme).toBe('light')
    const stored = JSON.parse(window.localStorage.getItem('strata.prefs.v1') ?? '{}')
    expect(stored.theme).toBe('light')
  })

  it('survives localStorage throwing on write (quota, private mode, etc.)', () => {
    const spy = vi.spyOn(window.localStorage, 'setItem').mockImplementation(() => {
      throw new DOMException('quota exceeded')
    })
    expect(() => usePrefs.getState().toggleUnits()).not.toThrow()
    expect(usePrefs.getState().units).toBe('oilfield') // store state still updates in-memory
    spy.mockRestore()
  })
})
