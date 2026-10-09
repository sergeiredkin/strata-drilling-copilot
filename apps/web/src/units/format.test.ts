import { describe, expect, it } from 'vitest'
import type { Quantity } from '../contracts/types'
import { formatQuantity } from './format'

function q(value: number | null, unit: Quantity['unit'], precision?: number): Quantity {
  return { value, unit, evidence_id: 'ev_0000000000', precision }
}

describe('formatQuantity', () => {
  it('formats a metric value with its own unit', () => {
    const f = formatQuantity(q(1234.5, 'kN', 1), 'metric')
    expect(f.text).toBe('1,234.5')
    expect(f.unit).toBe('kN')
    expect(f.display).toBe('1,234.5 kN')
  })

  it('converts to oilfield units', () => {
    const f = formatQuantity(q(100, 'bar', 1), 'oilfield')
    expect(f.unit).toBe('psi')
    expect(f.text).toBe('1,450.4')
  })

  it('defaults precision to 2 when not given', () => {
    const f = formatQuantity(q(1, 'kN'), 'metric')
    expect(f.text).toBe('1.00')
  })

  it('renders null as an em dash with no unit', () => {
    const f = formatQuantity(q(null, 'kN'), 'metric')
    expect(f.text).toBe('—')
    expect(f.unit).toBe('')
    expect(f.display).toBe('—')
  })

  it('hides the dimensionless unit "1"', () => {
    const f = formatQuantity(q(0.91, '1', 2), 'metric')
    expect(f.unit).toBe('')
    expect(f.display).toBe('0.91')
  })
})
