import '@testing-library/jest-dom/vitest'
import 'vitest-axe/extend-expect'

// jsdom doesn't implement matchMedia; uPlot calls it at construction time to track
// devicePixelRatio changes. Stubbed so any test that mounts a chart component doesn't crash.
if (typeof window !== 'undefined' && !window.matchMedia) {
  window.matchMedia = (query: string) => ({
    matches: false,
    media: query,
    onchange: null,
    addListener: () => undefined,
    removeListener: () => undefined,
    addEventListener: () => undefined,
    removeEventListener: () => undefined,
    dispatchEvent: () => false,
  })
}
