// Accessibility — docs/08_TESTING_AND_ACCEPTANCE.md §1 ("A11y | @axe-core/playwright | every
// route, both themes") and T10.3. Accept: zero serious/critical violations.
//
// Theme is set via localStorage (the same `strata.prefs.v1` key usePrefs persists to — see
// src/state/prefs.ts) before each navigation, not through a UI control: no component currently
// calls `usePrefs().setTheme`/`toggleTheme` (the store and the `[data-theme="light"]` CSS exist,
// but nothing in the app renders a toggle yet — a real gap, not something to fake a click path
// for here).
import AxeBuilder from '@axe-core/playwright'
import { expect, test, type Page } from '@playwright/test'

const WELL = '15_9-F-11_A'

const ROUTES = [
  '/field',
  `/well/${WELL}/workspace`,
  `/well/${WELL}/performance`,
  `/well/${WELL}/formation`,
  `/well/${WELL}/td`,
  `/well/${WELL}/mse`,
  `/well/${WELL}/trips`,
  '/issues',
  '/trust',
]

async function setTheme(page: Page, theme: 'dark' | 'light') {
  await page.addInitScript(
    (t) => window.localStorage.setItem('strata.prefs.v1', JSON.stringify({ units: 'metric', theme: t })),
    theme,
  )
}

for (const theme of ['dark', 'light'] as const) {
  test.describe(`a11y — ${theme} theme`, () => {
    for (const route of ROUTES) {
      test(`${route} has no serious/critical violations`, async ({ page }) => {
        await setTheme(page, theme)
        await page.goto(`${route}?fast=1`)
        await page.waitForTimeout(500) // lazy chunks (S3/S5) + initial data fetch to settle

        const results = await new AxeBuilder({ page })
          .withTags(['wcag2a', 'wcag2aa'])
          .analyze()

        const severe = results.violations.filter((v) => v.impact === 'serious' || v.impact === 'critical')
        const summary = severe.map((v) => `${v.id} (${v.impact}): ${v.nodes.length} node(s) — ${v.help}`).join('\n')
        expect(severe, summary).toHaveLength(0)
      })
    }
  })
}
