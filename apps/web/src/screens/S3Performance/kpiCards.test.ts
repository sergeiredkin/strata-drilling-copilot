import { describe, expect, it } from 'vitest'
import type { KpiReport, Quantity } from '../../contracts/types'
import { buildDisplayCards } from './kpiCards'

function q(value: number | null, unit: Quantity['unit']): Quantity {
  return { value, unit, evidence_id: 'ev_0000000000', precision: 2 }
}

function report(overrides: Partial<Record<string, Quantity>> = {}): KpiReport {
  const names = [
    'conn_s2s', 'conn_w2w', 'trip_in_open', 'trip_out_open',
    'trip_in_cased', 'trip_out_cased', 'flat_time_pct', 'on_bottom_pct',
  ] as const
  return {
    well: 'x',
    confidence: { level: 'high', reason: '' },
    distributions: [],
    cards: names.map((kpi) => ({
      kpi,
      value: overrides[kpi] ?? q(1, 'min'),
      best: q(0.5, 'min'),
      confidence: { level: 'high', reason: '' },
    })),
  }
}

describe('buildDisplayCards', () => {
  it('maps the 4 display cards from the 8 raw cards', () => {
    const cards = buildDisplayCards(report())
    expect(cards.map((c) => c.name)).toEqual([
      'Connection time',
      'Tripping speed',
      'Flat time',
      'On-bottom drilling',
    ])
  })

  it('Connection time uses conn_s2s as the main value', () => {
    const cards = buildDisplayCards(report({ conn_s2s: q(6.15, 'min') }))
    expect(cards[0]?.value.value).toBe(6.15)
    expect(cards[0]?.subKpi).toBe('conn_w2w')
  })

  it('Tripping speed uses trip_in_open as the main value', () => {
    const cards = buildDisplayCards(report({ trip_in_open: q(412, 'm/h') }))
    expect(cards[1]?.value.value).toBe(412)
  })

  it('Flat time and On-bottom drilling use static sub-lines', () => {
    const cards = buildDisplayCards(report())
    expect(cards[2]?.subStatic).toMatch(/off-bottom/)
    expect(cards[3]?.subStatic).toMatch(/rotary/)
  })

  it('missing cards fall back to a null Quantity and insufficient confidence, never a crash', () => {
    const minimal: KpiReport = { well: 'x', confidence: { level: 'high', reason: '' }, cards: [], distributions: [] }
    const cards = buildDisplayCards(minimal)
    expect(cards.every((c) => c.value.value === null)).toBe(true)
    expect(cards.every((c) => c.confidence.level === 'insufficient')).toBe(true)
  })
})
