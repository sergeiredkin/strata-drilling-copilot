// T11.4 offset compare — pure band-layout logic, no component code, so the two alignment modes
// (true MD vs. flattened on tops) are each independently testable.
import type { FormationReport } from '../../contracts/types'
import { mdToY } from './depthScale'

export type Band = { name: string; y0: number; y1: number }

/** Every well drawn on the same real-MD scale (`mdMin`/`mdMax` spanning every selected well) —
 * "offset wells side by side" in their true depth relationship, gaps where one well's tops
 * don't cover a depth the others do. */
export function mdBands(tops: FormationReport['tops'], mdMin: number, mdMax: number, heightPx: number): Band[] {
  return tops.map((t) => ({
    name: t.name,
    y0: mdToY(t.md_top, mdMin, mdMax, heightPx),
    y1: mdToY(t.md_base, mdMin, mdMax, heightPx),
  }))
}

/** The union of formation names across every selected well's tops, in first-seen order — the
 * reference well (first in the selection) contributes its own order first, so the common case
 * (comparing wells that share a formation column) reads top-to-bottom the way the reference
 * well's own stratigraphy does; names only some other well has are appended, never dropped. */
export function buildFormationOrder(wellsTops: FormationReport['tops'][]): string[] {
  const order: string[] = []
  for (const tops of wellsTops) {
    for (const t of tops) {
      if (!order.includes(t.name)) order.push(t.name)
    }
  }
  return order
}

/** Each formation gets an equal-height row (`heightPx / order.length`), in `order`'s position —
 * a correlation panel, not a depth scale. A well missing a formation in `order` simply has no
 * band in that row (honest gap), never a guessed position. */
export function flattenBands(tops: FormationReport['tops'], order: string[], heightPx: number): Band[] {
  const n = order.length
  if (n === 0) return []
  const bands: Band[] = []
  for (const t of tops) {
    const idx = order.indexOf(t.name)
    if (idx === -1) continue
    bands.push({ name: t.name, y0: (idx / n) * heightPx, y1: ((idx + 1) / n) * heightPx })
  }
  return bands
}
