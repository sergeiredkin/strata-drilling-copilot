// Performance budgets — docs/08_TESTING_AND_ACCEPTANCE.md §4 (T10.2). Run against the same
// `vite build && vite preview` static-mode server as demo.spec.ts.
//
// Deviation from §4's "30-day fixture": no well in the current fixtures spans 30 days (the
// richest, 15_9-F-11_A, spans ~4 days — see pipeline/strata_pipeline/fixtures/synth.py). Per
// CLAUDE.md, that's not faked here; the render/pan budgets below run against the real, smaller
// fixture and will need re-validation once real multi-week Volve wells are ingested (T10.4).
//
// Headless Chromium has no real compositor vsync, so the pan/zoom "fps" test measures whether
// the main thread keeps up with scripted wheel input (no long frame stalls) rather than true
// on-screen frame rate — still a meaningful regression signal for dropped/janky frames, just not
// a literal screen fps reading.
import { existsSync, readdirSync, readFileSync, statSync } from 'node:fs'
import { dirname, resolve } from 'node:path'
import { fileURLToPath } from 'node:url'
import { gzipSync } from 'node:zlib'
import { expect, test } from '@playwright/test'

const __dirname = dirname(fileURLToPath(import.meta.url))
const DIST = resolve(__dirname, '../dist')
const DATA_WELLS = resolve(__dirname, '../public/data/wells')

function dirSizeBytes(dir: string): number {
  let total = 0
  for (const entry of readdirSync(dir, { withFileTypes: true })) {
    const p = resolve(dir, entry.name)
    total += entry.isDirectory() ? dirSizeBytes(p) : statSync(p).size
  }
  return total
}

test.describe('Performance budgets', () => {
  test('initial route JS is <= 450 kB gzip (ECharts/S3/S5 lazy-loaded)', () => {
    test.skip(!existsSync(DIST), 'run `pnpm build` first (make e2e does this)')
    const indexHtml = readFileSync(resolve(DIST, 'index.html'), 'utf-8')
    const scriptSrcs = [...indexHtml.matchAll(/<script[^>]+src="([^"]+\.js)"/g)].map((m) => m[1])
    expect(scriptSrcs.length).toBeGreaterThan(0)

    let totalGzip = 0
    for (const src of scriptSrcs) {
      const file = resolve(DIST, src.replace(/^\//, ''))
      totalGzip += gzipSync(readFileSync(file)).length
    }
    expect(totalGzip, `${(totalGzip / 1024).toFixed(0)} kB gzip referenced directly from index.html`).toBeLessThanOrEqual(
      450 * 1024,
    )
  })

  test('static export is <= 25 MB per well', () => {
    const wells = readdirSync(DATA_WELLS, { withFileTypes: true }).filter((e) => e.isDirectory())
    expect(wells.length).toBeGreaterThan(0)
    for (const well of wells) {
      const bytes = dirSizeBytes(resolve(DATA_WELLS, well.name))
      expect(bytes, `${well.name}: ${(bytes / 1024 / 1024).toFixed(1)} MB`).toBeLessThanOrEqual(25 * 1024 * 1024)
    }
  })

  test('S2 Workspace first meaningful render <= 1.5s (cache warm)', async ({ page }) => {
    // First navigation warms the HTTP cache (JS chunk, fonts, the well's fixture files).
    await page.goto('/well/15_9-F-11_A/workspace?fast=1')
    await expect(page.getByText('BIT DEPTH')).toBeVisible()

    const hookloadRow = page.locator('div.flex.border-b').filter({ hasText: 'Hookload' })
    const start = Date.now()
    await page.goto('/well/15_9-F-11_A/workspace?fast=1')
    // A real decoded value ("916.4 kN"), not the pre-data "—" placeholder.
    await expect(hookloadRow.getByText(/\d+\.\d+/)).toBeVisible()
    const elapsedMs = Date.now() - start

    expect(elapsedMs, `first meaningful render took ${elapsedMs} ms`).toBeLessThanOrEqual(1500)
  })

  test('S2 Workspace pan (wheel-zoom) sustains no long main-thread stalls over 3s', async ({ page }) => {
    await page.goto('/well/15_9-F-11_A/workspace?fast=1')
    await expect(page.getByText('BIT DEPTH')).toBeVisible()
    await page.waitForTimeout(500)

    const hookloadPlot = page
      .locator('div.flex.border-b')
      .filter({ hasText: 'Hookload' })
      .locator('div.relative')
      .first()
    const box = await hookloadPlot.boundingBox()
    if (!box) throw new Error('HOOKLOAD plot not found')
    await page.mouse.move(box.x + box.width / 2, box.y + box.height / 2)

    const samplesPromise = page.evaluate(
      () =>
        new Promise<number[]>((resolveSamples) => {
          const samples: number[] = []
          let last = performance.now()
          const deadline = last + 3000
          function tick() {
            const now = performance.now()
            samples.push(now - last)
            last = now
            if (now < deadline) requestAnimationFrame(tick)
            else resolveSamples(samples)
          }
          requestAnimationFrame(tick)
        }),
    )

    // Scripted alternating wheel-zoom for ~3s, matching 08_TESTING_AND_ACCEPTANCE.md §4.
    const deadline = Date.now() + 3000
    let direction = 1
    while (Date.now() < deadline) {
      await page.mouse.wheel(0, direction * 80)
      direction *= -1
      await page.waitForTimeout(40)
    }

    const frameGapsMs = await samplesPromise
    const sorted = [...frameGapsMs].sort((a, b) => a - b)
    const medianGapMs = sorted[Math.floor(sorted.length / 2)] ?? 0
    const medianFps = 1000 / medianGapMs

    expect(medianFps, `median inter-frame gap ${medianGapMs.toFixed(1)} ms (${medianFps.toFixed(0)} fps)`).toBeGreaterThanOrEqual(
      50,
    )
  })
})
