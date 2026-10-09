import { describe, expect, it } from 'vitest'
import { EMPTY_VIEW_STATE, searchParamsToView, viewToSearchParams, type ViewState } from './view'

describe('view <-> URL search params', () => {
  it('round-trips a full state', () => {
    const state: ViewState = {
      timeRange: [100, 200],
      depthRange: [10, 20],
      panel: 'copilot',
      sessionId: 's1',
      evidenceId: 'ev_abc123',
      section: '12 1/4',
      issueId: 'iss_1',
      filters: { field: 'Volve', coverage: 'full' },
    }
    const params = viewToSearchParams(state)
    const back = searchParamsToView(params)
    expect(back).toEqual(state)
  })

  it('round-trips the empty state to an empty query string', () => {
    const params = viewToSearchParams(EMPTY_VIEW_STATE)
    expect(params.toString()).toBe('')
    expect(searchParamsToView(params)).toEqual(EMPTY_VIEW_STATE)
  })

  it('unknown query keys land in filters', () => {
    const params = new URLSearchParams('well=15_9-F-11_A&type=stuck_pipe')
    const state = searchParamsToView(params)
    expect(state.filters).toEqual({ well: '15_9-F-11_A', type: 'stuck_pipe' })
  })

  it('t0/t1 must both be present to form a timeRange', () => {
    const params = new URLSearchParams('t0=100')
    expect(searchParamsToView(params).timeRange).toBeNull()
  })
})
