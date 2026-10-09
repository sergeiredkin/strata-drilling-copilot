import { describe, expect, it } from 'vitest'
import { contrastRatio } from './contrast'
import { parseTokenBlocks } from './parseTokensCss'

const MIN_RATIO = 4.5

describe('token contrast (WCAG AA, body text)', () => {
  const blocks = parseTokenBlocks()

  const pairs: [text: string, bg: string][] = [
    ['--text', '--bg'],
    ['--text', '--panel'],
    ['--text', '--panel-2'],
    ['--text-2', '--bg'],
    ['--text-2', '--panel'],
    ['--link', '--bg'],
  ]

  for (const theme of ['dark', 'light'] as const) {
    describe(theme, () => {
      const tokens = blocks[theme]
      it('has every expected token', () => {
        for (const [a, b] of pairs) {
          expect(tokens[a], `${theme} ${a}`).toBeDefined()
          expect(tokens[b], `${theme} ${b}`).toBeDefined()
        }
      })

      for (const [textVar, bgVar] of pairs) {
        it(`${textVar} on ${bgVar} >= ${MIN_RATIO}:1`, () => {
          const text = tokens[textVar]
          const bg = tokens[bgVar]
          if (!text || !bg) throw new Error(`missing token for ${theme}`)
          expect(contrastRatio(text, bg)).toBeGreaterThanOrEqual(MIN_RATIO)
        })
      }
    })
  }
})
