import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import type { Reconciliation } from '../../contracts/types'
import { ReconciliationHeatmap } from './ReconciliationHeatmap'

describe('ReconciliationHeatmap', () => {
  it('shows an honest insufficient-data notice when scope=all has no rows', () => {
    const empty: Reconciliation = {
      scope: 'all',
      rows: [],
      cols: [],
      cells: [],
      agreement: [],
      tolerance: { boundary_slack_min: 5, min_duration_min: 2 },
    }
    render(<ReconciliationHeatmap reconciliation={empty} />)
    expect(screen.getAllByText(/No cross-well reconciliation export yet/).length).toBeGreaterThan(0)
  })

  it('collapses rig states into the 5-bucket grouping and marks the diagonal', () => {
    const data: Reconciliation = {
      scope: '15_9-F-11_A',
      rows: ['DRILL'],
      cols: ['rotary_drilling', 'sliding', 'connection'],
      cells: [
        [
          { minutes: { value: 70, unit: 'min', evidence_id: 'ev_1' }, pct: 70 },
          { minutes: { value: 10, unit: 'min', evidence_id: 'ev_2' }, pct: 10 },
          { minutes: { value: 20, unit: 'min', evidence_id: 'ev_3' }, pct: 20 },
        ],
      ],
      agreement: [],
      tolerance: { boundary_slack_min: 5, min_duration_min: 2 },
    }
    render(<ReconciliationHeatmap reconciliation={data} />)
    expect(screen.getByText('DRILL')).toBeInTheDocument()
    // rotary_drilling (70) + sliding (10) both collapse into the "Rotary" column.
    expect(screen.getByText('80 %')).toBeInTheDocument()
    expect(screen.getByText('20 %')).toBeInTheDocument()
  })
})
