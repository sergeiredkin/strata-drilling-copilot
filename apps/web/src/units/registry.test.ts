import { describe, expect, it } from 'vitest'
import type { Unit } from '../contracts/types'
import { convertibleUnits, convertValue, unitLabel } from './registry'

// Table from 04_DATA_CONTRACTS.md §1 — the normative source for every factor and oilfield label.
const TABLE: { unit: Unit; oilfieldUnit: string; factor: number }[] = [
  { unit: 'm', oilfieldUnit: 'ft', factor: 3.28084 },
  { unit: 'kN', oilfieldUnit: 'klbf', factor: 0.224809 },
  { unit: 'kN.m', oilfieldUnit: 'kft.lbf', factor: 0.737562 },
  { unit: 'bar', oilfieldUnit: 'psi', factor: 14.5038 },
  { unit: 'm/h', oilfieldUnit: 'ft/h', factor: 3.28084 },
  { unit: 'L/min', oilfieldUnit: 'gpm', factor: 0.264172 },
  { unit: 'sg', oilfieldUnit: 'ppg', factor: 8.3454 },
  { unit: 'MPa', oilfieldUnit: 'psi', factor: 145.038 },
]

describe('unit conversion table (both ways)', () => {
  for (const { unit, oilfieldUnit, factor } of TABLE) {
    it(`${unit} -> ${oilfieldUnit} (metric SI value unchanged, oilfield applies the factor)`, () => {
      const metric = convertValue(10, unit, 'metric')
      expect(metric).toEqual({ value: 10, unit })

      const oilfield = convertValue(10, unit, 'oilfield')
      expect(oilfield.unit).toBe(oilfieldUnit)
      expect(oilfield.value).toBeCloseTo(10 * factor, 6)
    })

    it(`${unit}: unitLabel matches convertValue's unit in both systems`, () => {
      expect(unitLabel(unit, 'metric')).toBe(unit)
      expect(unitLabel(unit, 'oilfield')).toBe(oilfieldUnit)
    })

    it(`${unit}: round-trips back to the original SI value within tolerance`, () => {
      const { value: oilfieldValue, unit: oilfieldLabel } = convertValue(10, unit, 'oilfield')
      expect(oilfieldLabel).toBe(oilfieldUnit)
      const backToSi = (oilfieldValue ?? 0) / factor
      expect(backToSi).toBeCloseTo(10, 6)
    })
  }

  it('convertibleUnits() enumerates exactly the table above', () => {
    expect(new Set(convertibleUnits())).toEqual(new Set(TABLE.map((t) => t.unit)))
  })
})

describe('units with no oilfield mapping pass through unchanged', () => {
  const passthrough: Unit[] = ['rpm', 'min', 'h', 's', '%', 'm/s', '1', 'degC', 'deg']

  for (const unit of passthrough) {
    it(`${unit} is identical in both systems`, () => {
      expect(convertValue(5, unit, 'metric')).toEqual({ value: 5, unit })
      expect(convertValue(5, unit, 'oilfield')).toEqual({ value: 5, unit })
      expect(unitLabel(unit, 'oilfield')).toBe(unit)
    })
  }
})

describe('null values', () => {
  it('convertValue passes null through without converting', () => {
    expect(convertValue(null, 'm', 'oilfield')).toEqual({ value: null, unit: 'ft' })
  })
})
