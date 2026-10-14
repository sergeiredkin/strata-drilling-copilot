import { act, renderHook } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import type { ReplayEvent } from '../../contracts/types'
import { useReplayToasts } from './useReplayToasts'

function alertEvent(id: string, message = 'something happened'): ReplayEvent {
  return { type: 'alert', t: 0, alert: { id, kind: 'data_gap', message } }
}

function stateEvent(): ReplayEvent {
  return { type: 'state', t: 0, state: 'rotary_drilling' }
}

describe('useReplayToasts', () => {
  it('ignores non-alert events', () => {
    const { result } = renderHook(() => useReplayToasts())
    act(() => result.current.push(stateEvent()))
    expect(result.current.toasts).toHaveLength(0)
  })

  it('adds an alert as a toast', () => {
    const { result } = renderHook(() => useReplayToasts())
    act(() => result.current.push(alertEvent('a1', 'data gap')))
    expect(result.current.toasts).toHaveLength(1)
    expect(result.current.toasts[0]?.message).toBe('data gap')
  })

  it('caps visible toasts at 3, dropping the oldest', () => {
    const { result } = renderHook(() => useReplayToasts())
    act(() => {
      result.current.push(alertEvent('a1'))
      result.current.push(alertEvent('a2'))
      result.current.push(alertEvent('a3'))
      result.current.push(alertEvent('a4'))
    })
    expect(result.current.toasts).toHaveLength(3)
    expect(result.current.toasts.map((t) => t.id)).toEqual(
      expect.arrayContaining([expect.stringContaining('a2'), expect.stringContaining('a3'), expect.stringContaining('a4')]),
    )
  })

  it('dismisses a toast by id', () => {
    const { result } = renderHook(() => useReplayToasts())
    act(() => result.current.push(alertEvent('a1')))
    const id = result.current.toasts[0]?.id as string
    act(() => result.current.dismiss(id))
    expect(result.current.toasts).toHaveLength(0)
  })
})
