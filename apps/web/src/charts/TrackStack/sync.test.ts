import { describe, expect, it, vi } from 'vitest'
import { createTimeRangeSync } from './sync'

describe('createTimeRangeSync', () => {
  it('starts with the initial range', () => {
    const sync = createTimeRangeSync([0, 100])
    expect(sync.getRange()).toEqual([0, 100])
  })

  it('notifies subscribers with the new range and the origin', () => {
    const sync = createTimeRangeSync([0, 100])
    const listener = vi.fn()
    sync.subscribe(listener)

    const origin = Symbol('track-a')
    sync.setRange([10, 110], origin)

    expect(listener).toHaveBeenCalledWith([10, 110], origin)
    expect(sync.getRange()).toEqual([10, 110])
  })

  it('unsubscribe stops further notifications', () => {
    const sync = createTimeRangeSync([0, 100])
    const listener = vi.fn()
    const unsubscribe = sync.subscribe(listener)
    unsubscribe()

    sync.setRange([10, 110])
    expect(listener).not.toHaveBeenCalled()
  })

  it('two independent sync instances never cross-talk', () => {
    const a = createTimeRangeSync([0, 100])
    const b = createTimeRangeSync([0, 100])
    const listenerB = vi.fn()
    b.subscribe(listenerB)

    a.setRange([50, 150])

    expect(listenerB).not.toHaveBeenCalled()
    expect(b.getRange()).toEqual([0, 100])
  })
})
