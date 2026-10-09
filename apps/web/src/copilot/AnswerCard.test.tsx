import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import type { CopilotAnswer } from '../contracts/types'
import { AnswerCard } from './AnswerCard'

const BASE: CopilotAnswer = {
  kind: 'answer',
  answer: 'Connections drove most of the lost time.',
  claims: [
    { text: 'Total invisible lost time', value: 14.96, unit: 'h', evidence_id: 'ev_1', verified: true },
  ],
  ddr_quotes: [],
  reasoning: 'Aggregated rig-state intervals vs composite best.',
  assumptions: ['Composite best = P10 of section connections.'],
  confidence: 'high',
  confidence_reason: 'Dense sensor coverage.',
  trace: [],
}

describe('AnswerCard', () => {
  it('renders the answer sections for kind=answer', () => {
    render(<AnswerCard answer={BASE} />)
    expect(screen.getByText('Connections drove most of the lost time.')).toBeInTheDocument()
    expect(screen.getByText('Total invisible lost time')).toBeInTheDocument()
    expect(screen.getByText(/14.96/)).toBeInTheDocument()
    expect(screen.getByText(/Aggregated rig-state/)).toBeInTheDocument()
    expect(screen.getByText(/Composite best = P10/)).toBeInTheDocument()
    expect(screen.getByText('High')).toBeInTheDocument()
  })

  it('shows the failed-verifier footer when unverified_numbers_in_text is present', () => {
    const answer: CopilotAnswer = {
      ...BASE,
      claims: [
        {
          text: 'Total invisible lost time',
          value: 19.4,
          unit: 'h',
          evidence_id: 'ev_1',
          verified: false,
          verify_note: 'evidence records 14.96 h, not 19.4 h',
        },
      ],
      unverified_numbers_in_text: ['19.4'],
    }
    render(<AnswerCard answer={answer} />)
    expect(screen.getByText(/1 number failed the verifier/)).toBeInTheDocument()
  })

  it('renders a notice card for kind=insufficient_data', () => {
    const answer: CopilotAnswer = { ...BASE, kind: 'insufficient_data', answer: 'No trip data.' }
    render(<AnswerCard answer={answer} />)
    expect(screen.getByText('Insufficient data')).toBeInTheDocument()
    expect(screen.getByText('No trip data.')).toBeInTheDocument()
    expect(screen.queryByText('Reasoning')).not.toBeInTheDocument()
  })

  it('renders a notice card for kind=live_mode_required', () => {
    const answer: CopilotAnswer = { ...BASE, kind: 'live_mode_required', answer: 'Needs live mode.' }
    render(<AnswerCard answer={answer} />)
    expect(screen.getByText('Live mode required')).toBeInTheDocument()
  })

  it('renders a notice card for kind=out_of_scope', () => {
    const answer: CopilotAnswer = { ...BASE, kind: 'out_of_scope', answer: 'Advisory only, no setpoints.' }
    render(<AnswerCard answer={answer} />)
    expect(screen.getByText('Out of scope — advisory only')).toBeInTheDocument()
  })
})
