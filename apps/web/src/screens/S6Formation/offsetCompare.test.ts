import { describe, expect, it } from 'vitest'
import { buildFormationOrder, flattenBands, mdBands } from './offsetCompare'

const TOPS_A = [
  { name: 'Ty Fm.', md_top: 1000, md_base: 1100 },
  { name: 'Draupne Fm.', md_top: 1100, md_base: 1200 },
]
const TOPS_B = [
  { name: 'Draupne Fm.', md_top: 2000, md_base: 2050 },
  { name: 'Heather Fm.', md_top: 2050, md_base: 2150 },
]

describe('mdBands', () => {
  it('maps each top to its real-MD pixel band', () => {
    const bands = mdBands(TOPS_A, 1000, 1200, 200)
    expect(bands).toEqual([
      { name: 'Ty Fm.', y0: 0, y1: 100 },
      { name: 'Draupne Fm.', y0: 100, y1: 200 },
    ])
  })
})

describe('buildFormationOrder', () => {
  it("puts the reference well's own formations first, in its own order", () => {
    expect(buildFormationOrder([TOPS_A, TOPS_B])).toEqual(['Ty Fm.', 'Draupne Fm.', 'Heather Fm.'])
  })

  it('never drops a name only a later well has', () => {
    const order = buildFormationOrder([TOPS_A, TOPS_B])
    expect(order).toContain('Heather Fm.')
  })
})

describe('flattenBands', () => {
  const order = buildFormationOrder([TOPS_A, TOPS_B])

  it('gives every formation an equal-height row regardless of its real thickness', () => {
    const flatA = flattenBands(TOPS_A, order, 300)
    for (const b of flatA) expect(b.y1 - b.y0).toBeCloseTo(100, 6)
  })

  it('places the same formation name in the same row across wells', () => {
    const flatA = flattenBands(TOPS_A, order, 300)
    const flatB = flattenBands(TOPS_B, order, 300)
    const draupneA = flatA.find((b) => b.name === 'Draupne Fm.')
    const draupneB = flatB.find((b) => b.name === 'Draupne Fm.')
    expect(draupneA).toEqual(draupneB)
  })

  it('omits a formation the well has no pick for, rather than guessing a row', () => {
    const flatB = flattenBands(TOPS_B, order, 300)
    expect(flatB.find((b) => b.name === 'Ty Fm.')).toBeUndefined()
  })

  it('returns an empty array for an empty order', () => {
    expect(flattenBands(TOPS_A, [], 300)).toEqual([])
  })
})
