// The URL-synced view store — docs/03_ARCHITECTURE.md §3.2. `wellId`/screen live in the router
// path (`/well/:id/workspace`, etc.), not here; this store only owns what each route's own query
// string carries: time/depth window, panel, evidence/session ids, section, issue, and generic
// filters (S1's field/coverage filters, S7's well/type/formation query — anything else).
import { create } from 'zustand'

export type ViewState = {
  timeRange: [number, number] | null
  depthRange: [number, number] | null
  panel: string | null
  sessionId: string | null
  evidenceId: string | null
  section: string | null
  issueId: string | null
  filters: Record<string, string>
  /** A question another screen wants the copilot dock to ask once it opens, e.g. a mismatch's
   * "Ask copilot why" (docs/02_IMPLEMENTATION_PLAN.md T8.2). Not URL-synced — it's a one-shot
   * handoff the dock consumes and clears, not durable view state. */
  copilotPrefill: string | null
}

export type ViewActions = {
  setTimeRange: (range: [number, number] | null) => void
  setDepthRange: (range: [number, number] | null) => void
  setPanel: (panel: string | null) => void
  setSessionId: (id: string | null) => void
  setEvidenceId: (id: string | null) => void
  setSection: (section: string | null) => void
  setIssueId: (id: string | null) => void
  setFilter: (key: string, value: string | null) => void
  setCopilotPrefill: (question: string | null) => void
  replaceState: (state: ViewState) => void
}

export const EMPTY_VIEW_STATE: ViewState = {
  timeRange: null,
  depthRange: null,
  panel: null,
  sessionId: null,
  evidenceId: null,
  section: null,
  issueId: null,
  filters: {},
  copilotPrefill: null,
}

export const useView = create<ViewState & ViewActions>((set, get) => ({
  ...EMPTY_VIEW_STATE,
  setTimeRange: (timeRange) => set({ timeRange }),
  setDepthRange: (depthRange) => set({ depthRange }),
  setPanel: (panel) => set({ panel }),
  setSessionId: (sessionId) => set({ sessionId }),
  setEvidenceId: (evidenceId) => set({ evidenceId }),
  setSection: (section) => set({ section }),
  setIssueId: (issueId) => set({ issueId }),
  setCopilotPrefill: (copilotPrefill) => set({ copilotPrefill }),
  setFilter: (key, value) => {
    const next: Record<string, string> = {}
    for (const [k, v] of Object.entries(get().filters)) {
      if (k !== key) next[k] = v
    }
    if (value !== null) next[key] = value
    set({ filters: next })
  },
  replaceState: (state) => set(state),
}))

const KNOWN_KEYS = ['t0', 't1', 'd0', 'd1', 'panel', 's', 'ev', 'section', 'issue'] as const

export function viewToSearchParams(state: ViewState): URLSearchParams {
  const params = new URLSearchParams()
  if (state.timeRange) {
    params.set('t0', String(state.timeRange[0]))
    params.set('t1', String(state.timeRange[1]))
  }
  if (state.depthRange) {
    params.set('d0', String(state.depthRange[0]))
    params.set('d1', String(state.depthRange[1]))
  }
  if (state.panel) params.set('panel', state.panel)
  if (state.sessionId) params.set('s', state.sessionId)
  if (state.evidenceId) params.set('ev', state.evidenceId)
  if (state.section) params.set('section', state.section)
  if (state.issueId) params.set('issue', state.issueId)
  for (const [key, value] of Object.entries(state.filters)) {
    if (value) params.set(key, value)
  }
  return params
}

export function searchParamsToView(params: URLSearchParams): ViewState {
  const t0 = params.get('t0')
  const t1 = params.get('t1')
  const d0 = params.get('d0')
  const d1 = params.get('d1')
  const filters: Record<string, string> = {}
  for (const [key, value] of params.entries()) {
    if (!(KNOWN_KEYS as readonly string[]).includes(key)) filters[key] = value
  }
  return {
    timeRange: t0 !== null && t1 !== null ? [Number(t0), Number(t1)] : null,
    depthRange: d0 !== null && d1 !== null ? [Number(d0), Number(d1)] : null,
    panel: params.get('panel'),
    sessionId: params.get('s'),
    evidenceId: params.get('ev'),
    section: params.get('section'),
    issueId: params.get('issue'),
    filters,
    copilotPrefill: null,
  }
}
