import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import type { EvalReport } from '../../contracts/types'
import { AblationTable } from './AblationTable'

const REPORT: EvalReport = {
  qc: [],
  rigstate_agreement: [],
  gold_set: { n_questions: 0, version: '0.0', author: 'pending', status: 'pending' },
  ablation: [
    {
      config: 'full',
      metrics: {
        answer_correctness: null,
        numbers_verified_pct: null,
        unsupported_numbers: null,
        correct_insufficient_pct: null,
        median_latency_s: null,
      },
    },
  ],
}

describe('AblationTable', () => {
  it('renders every null metric as "—", never a fabricated score', () => {
    render(<AblationTable report={REPORT} />)
    const dashes = screen.getAllByText('—')
    expect(dashes).toHaveLength(5)
  })

  it('explains the empty state when the gold set is pending', () => {
    render(<AblationTable report={REPORT} />)
    expect(screen.getByText(/Empty until the gold set exists/)).toBeInTheDocument()
  })

  it('shows a status line instead once the gold set is no longer pending', () => {
    const report: EvalReport = {
      ...REPORT,
      gold_set: { n_questions: 40, version: '1.0', author: 'J. Doe', status: 'draft' },
    }
    render(<AblationTable report={report} />)
    expect(screen.getByText(/Gold set status: draft\./)).toBeInTheDocument()
  })
})
