import { renderHook } from '@testing-library/react'
import { act, waitFor } from '@testing-library/react'
import { beforeAll, beforeEach, describe, expect, it, vi } from 'vitest'
import { createTimeRangeSync } from '../../charts/TrackStack/sync'
import { installFixtureFetch } from '../../test/fixtureFetch'
import { useReplay } from '../../state/replay'
import { useReplayRunner } from './useReplayRunner'

const WELL = '15_9-F-11_A'

beforeAll(() => {
  installFixtureFetch()
  window.history.replaceState({}, '', '/?fast=1') // collapse replay delays for this test
})

beforeEach(() => {
  useReplay.getState().reset()
})

describe('useReplayRunner', () => {
  it('advances t and calls onRangeSettled as events stream in', async () => {
    const fullRange: [number, number] = [0, 400_000_000_000]
    const sync = createTimeRangeSync(fullRange)
    const onRangeSettled = vi.fn()
    const { result } = renderHook(() => useReplayRunner(WELL, fullRange, sync, onRangeSettled, vi.fn()))

    act(() => {
      result.current.start(1_369_000_000_000) // somewhere inside the real well's span
    })

    await waitFor(() => expect(useReplay.getState().t).not.toBeNull())
    await waitFor(() => expect(onRangeSettled).toHaveBeenCalled())
    result.current.stop()
  })

  it('does nothing when wellId or fullRange is missing', () => {
    const sync = createTimeRangeSync([0, 1])
    const onRangeSettled = vi.fn()
    const { result } = renderHook(() => useReplayRunner(undefined, null, sync, onRangeSettled, vi.fn()))
    act(() => result.current.start(0))
    expect(useReplay.getState().playing).toBe(false)
  })

  it('stop() pauses the store', async () => {
    const fullRange: [number, number] = [0, 400_000_000_000]
    const sync = createTimeRangeSync(fullRange)
    const { result } = renderHook(() => useReplayRunner(WELL, fullRange, sync, vi.fn(), vi.fn()))
    act(() => result.current.start(1_369_000_000_000))
    await waitFor(() => expect(useReplay.getState().playing).toBe(true))
    result.current.stop()
    expect(useReplay.getState().playing).toBe(false)
  })
})
