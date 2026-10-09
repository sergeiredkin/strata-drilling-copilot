import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import type { EvalReport } from '../../contracts/types'
import { QcTable } from './QcTable'

const REPORT: EvalReport = {
  qc: [
    {
      well: '15_9-F-11_A',
      gap_hours: { value: 0.27, unit: 'h', evidence_id: 'ev_1', precision: 2 },
      spikes_removed: 0,
      unit_fixes: 0,
      sentinels_removed: 0,
    },
  ],
  rigstate_agreement: [{ well: '15_9-F-11_A', agreement: null }],
  gold_set: { n_questions: 0, version: '0.0', author: 'pending', status: 'pending' },
  ablation: [],
}

describe('QcTable', () => {
  it('renders "—" for a null rig-state agreement instead of fabricating a number', () => {
    render(<QcTable report={REPORT} />)
    expect(screen.getByText('15_9-F-11_A')).toBeInTheDocument()
    expect(screen.getByText('—')).toBeInTheDocument()
  })

  it('renders a percentage when agreement is present', () => {
    const report: EvalReport = {
      ...REPORT,
      rigstate_agreement: [
        { well: '15_9-F-11_A', agreement: { value: 87, unit: '%', evidence_id: 'ev_2' } },
      ],
    }
    render(<QcTable report={report} />)
    expect(screen.getByText('87 %')).toBeInTheDocument()
  })
})
