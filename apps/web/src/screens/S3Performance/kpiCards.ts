// Maps the 8 raw KpiReport cards (docs/04_DATA_CONTRACTS.md KpiName) onto the 4 display cards
// from the S3 comp (Connection time, Tripping speed, Flat time, On-bottom drilling). Pure so
// it's unit-testable without rendering anything.
import type { Confidence, KpiReport, Quantity } from '../../contracts/types'

export type DisplayKpiCard = {
  name: string
  value: Quantity
  best: Quantity | null
  confidence: Confidence
  subKpi: 'conn_w2w' | 'trip_cased' | 'static'
  subStatic?: string
}

function findCard(report: KpiReport, kpi: string) {
  return report.cards.find((c) => c.kpi === kpi)
}

const NULL_QUANTITY = (unit: Quantity['unit']): Quantity => ({ value: null, unit, evidence_id: 'ev_0000000000' })
const INSUFFICIENT: Confidence = { level: 'insufficient', reason: 'no data for this KPI', rule_ids: [] }

export function buildDisplayCards(report: KpiReport): DisplayKpiCard[] {
  const connS2s = findCard(report, 'conn_s2s')
  const tripInOpen = findCard(report, 'trip_in_open')
  const flatTime = findCard(report, 'flat_time_pct')
  const onBottom = findCard(report, 'on_bottom_pct')

  return [
    {
      name: 'Connection time',
      value: connS2s?.value ?? NULL_QUANTITY('min'),
      best: connS2s?.best ?? null,
      confidence: connS2s?.confidence ?? INSUFFICIENT,
      subKpi: 'conn_w2w',
    },
    {
      name: 'Tripping speed',
      value: tripInOpen?.value ?? NULL_QUANTITY('m/h'),
      best: tripInOpen?.best ?? null,
      confidence: tripInOpen?.confidence ?? INSUFFICIENT,
      subKpi: 'trip_cased',
    },
    {
      name: 'Flat time',
      value: flatTime?.value ?? NULL_QUANTITY('%'),
      best: flatTime?.best ?? null,
      confidence: flatTime?.confidence ?? INSUFFICIENT,
      subKpi: 'static',
      subStatic: 'off-bottom, not tripping, not drilling',
    },
    {
      name: 'On-bottom drilling',
      value: onBottom?.value ?? NULL_QUANTITY('%'),
      best: onBottom?.best ?? null,
      confidence: onBottom?.confidence ?? INSUFFICIENT,
      subKpi: 'static',
      subStatic: 'rotary + sliding',
    },
  ]
}
