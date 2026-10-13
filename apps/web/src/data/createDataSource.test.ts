import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

// Regression: the deployed GitHub Pages build 404s on every data fetch if StaticSource is
// constructed with a hardcoded '/data' instead of respecting the Vite base path — confirmed
// live (curl) against https://sergeiredkin.github.io/strata-drilling-copilot/, see
// docs/audits/2026-10-13_STRATA_ENGINEERING_AUDIT.md P0-02.
describe('createDataSource', () => {
  const originalFetch = globalThis.fetch

  beforeEach(() => {
    globalThis.fetch = vi.fn(
      async () => new Response(JSON.stringify({ wells: [], generated_at: 'x' }), { status: 200 }),
    ) as unknown as typeof fetch
  })

  afterEach(() => {
    globalThis.fetch = originalFetch
    vi.unstubAllEnvs()
  })

  it('fetches relative to the Vite base path, not an absolute /data root', async () => {
    vi.stubEnv('BASE_URL', '/strata-drilling-copilot/')
    const { createDataSource } = await import('./createDataSource')
    await createDataSource().wells()
    const calledUrl = (globalThis.fetch as unknown as ReturnType<typeof vi.fn>).mock.calls[0]?.[0] as string
    expect(calledUrl).toBe('/strata-drilling-copilot/data/wells.json')
  })

  it('defaults to /data at the root base path (local dev / vite preview)', async () => {
    vi.stubEnv('BASE_URL', '/')
    vi.resetModules()
    const { createDataSource } = await import('./createDataSource')
    await createDataSource().wells()
    const calledUrl = (globalThis.fetch as unknown as ReturnType<typeof vi.fn>).mock.calls[0]?.[0] as string
    expect(calledUrl).toBe('/data/wells.json')
  })
})
