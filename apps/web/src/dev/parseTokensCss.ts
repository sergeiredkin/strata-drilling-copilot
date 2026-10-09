import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

const TOKENS_CSS_PATH = resolve(process.cwd(), 'src/styles/tokens.css')

export type ThemeName = 'dark' | 'light'

/** Parses `:root` / `:root[data-theme=...]` blocks out of tokens.css into {theme: {token: hex}}. */
export function parseTokenBlocks(css = readFileSync(TOKENS_CSS_PATH, 'utf-8')): Record<ThemeName, Record<string, string>> {
  const blocks: Record<ThemeName, Record<string, string>> = { dark: {}, light: {} }
  const blockRe = /:root(?:,\s*:root\[data-theme=['"]dark['"]\])?(?:\[data-theme=['"](dark|light)['"]\])?\s*\{([^}]*)\}/g
  let match: RegExpExecArray | null
  while ((match = blockRe.exec(css))) {
    const theme: ThemeName = match[1] === 'light' ? 'light' : 'dark'
    const body = match[2] ?? ''
    const varRe = /(--[a-z0-9-]+)\s*:\s*(#[0-9a-f]{6})\s*;/gi
    let varMatch: RegExpExecArray | null
    while ((varMatch = varRe.exec(body))) {
      const name = varMatch[1] as string
      const value = varMatch[2] as string
      blocks[theme][name] = value
    }
  }
  return blocks
}
