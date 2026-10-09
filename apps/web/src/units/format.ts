// Formats a Quantity for display — docs/04_DATA_CONTRACTS.md §1/§3, 05_DESIGN_SYSTEM.md §6
// (<Num> consumes this; built standalone here so it's usable before T4.4 builds <Num>).
import type { Quantity, Unit } from '../contracts/types'
import { convertValue, unitLabel, type UnitSystem } from './registry'

const DEFAULT_PRECISION = 2
const NULL_DISPLAY = '—' // em dash — "unknown, shown with a tooltip saying why"

function formatNumber(value: number, precision: number): string {
  return new Intl.NumberFormat('en-US', {
    minimumFractionDigits: precision,
    maximumFractionDigits: precision,
  }).format(value)
}

export type FormattedQuantity = {
  /** Numeric text only, or the null-display dash. */
  text: string
  /** Unit label in the requested system (empty string if the value is null). */
  unit: string
  /** `${text} ${unit}` (or just `text` when there's no unit to show), ready to render. */
  display: string
}

export function formatQuantity(q: Quantity, system: UnitSystem): FormattedQuantity {
  const precision = q.precision ?? DEFAULT_PRECISION
  const { value, unit } = convertValue(q.value, q.unit, system)
  if (value === null) {
    return { text: NULL_DISPLAY, unit: '', display: NULL_DISPLAY }
  }
  const text = formatNumber(value, precision)
  const showUnit = unit !== '1' // the dimensionless unit is never shown
  return { text, unit: showUnit ? unit : '', display: showUnit ? `${text} ${unit}` : text }
}

/** For axis labels / column headers where there's no value yet, just the unit text. */
export function axisUnitLabel(unit: Unit, system: UnitSystem): string {
  return unitLabel(unit, system)
}
