// Two-way useView <-> URL sync (docs/03_ARCHITECTURE.md §3.2): store changes debounce into a
// `history.replaceState` (150 ms, so typing/dragging doesn't spam history); back/forward
// (`popstate`) re-reads the URL into the store. Mount once per page, near the route root.
import { useEffect, useRef } from 'react'
import { useLocation } from 'react-router-dom'
import { searchParamsToView, useView, viewToSearchParams } from './view'

const DEBOUNCE_MS = 150

export function useViewUrlSync(): void {
  const location = useLocation()
  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null)
  const syncingFromUrl = useRef(false)

  // Initial parse + re-parse on every navigation (covers popstate too, since React Router's
  // useLocation updates on popstate).
  useEffect(() => {
    syncingFromUrl.current = true
    useView.getState().replaceState(searchParamsToView(new URLSearchParams(location.search)))
    syncingFromUrl.current = false
    // Only the search string matters here; pathname changes are handled by the router itself.
  }, [location.search])

  useEffect(() => {
    const unsubscribe = useView.subscribe((state) => {
      if (syncingFromUrl.current) return
      if (debounceRef.current) clearTimeout(debounceRef.current)
      debounceRef.current = setTimeout(() => {
        const next = viewToSearchParams(state).toString()
        const current = new URLSearchParams(window.location.search).toString()
        if (next !== current) {
          const url = `${window.location.pathname}${next ? `?${next}` : ''}`
          window.history.replaceState(null, '', url)
        }
      }, DEBOUNCE_MS)
    })
    return () => {
      unsubscribe()
      if (debounceRef.current) clearTimeout(debounceRef.current)
    }
  }, [])
}
