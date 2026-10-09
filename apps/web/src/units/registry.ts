// Unit conversion registry — docs/04_DATA_CONTRACTS.md §1. Everything stored/transmitted is SI
// (the `Unit` enum in contracts); the UI converts on display only. Units with no entry here
// (rpm, min, h, s, %, m/s, 1, degC, deg) are identical in both systems.
import type { Unit } from '../contracts/types'
import type { UnitSystem } from '../state/prefs'

export type { UnitSystem } from '../state/prefs'

type Conversion = {
  /** value_oilfield = value_SI * factor */
  factor: number
  oilfieldUnit: string
}

const CONVERSIONS: Partial<Record<Unit, Conversion>> = {
  m: { factor: 3.28084, oilfieldUnit: 'ft' },
  'm/h': { factor: 3.28084, oilfieldUnit: 'ft/h' },
  kN: { factor: 0.224809, oilfieldUnit: 'klbf' },
  'kN.m': { factor: 0.737562, oilfieldUnit: 'kft.lbf' },
  bar: { factor: 14.5038, oilfieldUnit: 'psi' },
  'L/min': { factor: 0.264172, oilfieldUnit: 'gpm' },
  sg: { factor: 8.3454, oilfieldUnit: 'ppg' },
  MPa: { factor: 145.038, oilfieldUnit: 'psi' },
}

export type ConvertedQuantity = {
  value: number | null
  unit: string
}

/** Converts an SI value to the given unit system. `metric` (and any unit with no oilfield
 * mapping) is a passthrough — the SI unit string doubles as its own label. */
export function convertValue(value: number | null, unit: Unit, system: UnitSystem): ConvertedQuantity {
  const conversion = system === 'oilfield' ? CONVERSIONS[unit] : undefined
  if (!conversion) return { value, unit }
  return { value: value === null ? null : value * conversion.factor, unit: conversion.oilfieldUnit }
}

/** The display unit label alone (for axis labels / column headers), without converting a value. */
export function unitLabel(unit: Unit, system: UnitSystem): string {
  if (system === 'oilfield') {
    const conversion = CONVERSIONS[unit]
    if (conversion) return conversion.oilfieldUnit
  }
  return unit
}

/** Every SI unit this registry knows how to convert to oilfield units — used by table-driven
 * tests and anywhere that needs to enumerate conversions (e.g. a units reference panel). */
export function convertibleUnits(): Unit[] {
  return Object.keys(CONVERSIONS) as Unit[]
}
