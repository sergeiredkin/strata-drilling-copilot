/// <reference types="vitest/config" />
import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

export default defineConfig({
  // GitHub Pages serves this app at https://<user>.github.io/strata-drilling-copilot/, a
  // subpath — only set when building for Pages (the GH Actions workflow sets this env var);
  // local dev/preview and `make export`'s static mode stay at the root path.
  base: process.env.GH_PAGES ? '/strata-drilling-copilot/' : '/',
  plugins: [react()],
  test: {
    environment: 'jsdom',
    globals: true,
    passWithNoTests: true,
    setupFiles: ['./src/test/setup.ts'],
    exclude: ['e2e/**', 'node_modules/**'],
  },
})
