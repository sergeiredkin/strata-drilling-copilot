// Static mode first (docs/01_PRODUCT_SPEC.md §4): live mode only switches on when VITE_API_URL
// is set. Both sources return identical shapes, so the rest of the app never branches on mode.
import type { DataSource } from './DataSource'
import { HttpSource } from './HttpSource'
import { StaticSource } from './StaticSource'

let instance: DataSource | null = null

export function createDataSource(): DataSource {
  const apiUrl = import.meta.env.VITE_API_URL
  // `BASE_URL` is "/" locally and under `vite preview`, but a subpath on GitHub Pages
  // (`/strata-drilling-copilot/`) — the exported data lives under that same base, not at the
  // domain root, so a hardcoded '/data' 404s there (confirmed: see docs/audits).
  return apiUrl ? new HttpSource(apiUrl) : new StaticSource(`${import.meta.env.BASE_URL}data`)
}

/** Lazily-created singleton for use outside React (e.g. query hook defaults). Components should
 * generally get the instance via a provider/context once T4.2 wires one up. */
export function getDataSource(): DataSource {
  if (!instance) instance = createDataSource()
  return instance
}

export function isLiveMode(): boolean {
  return Boolean(import.meta.env.VITE_API_URL)
}
