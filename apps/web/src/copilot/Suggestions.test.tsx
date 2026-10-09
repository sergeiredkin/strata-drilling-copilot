import { fireEvent, render, screen } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import type { CopilotContext, SessionIndex } from '../contracts/types'
import { Suggestions } from './Suggestions'

const INDEX: SessionIndex = {
  sessions: [
    {
      id: 's1',
      question: 'What drove the lost time?',
      context: { screen: 'performance', well: '15_9-F-11_A' },
      file: 'a.jsonl',
    },
    {
      id: 's2',
      question: 'One-line lost-time number?',
      context: { screen: 'performance', well: '15_9-F-11_A' },
      file: 'b.jsonl',
    },
    {
      id: 's3',
      question: 'How is formation picked?',
      context: { screen: 'formation', well: '15_9-F-11_A' },
      file: 'c.jsonl',
    },
  ],
}

const CTX: CopilotContext = { screen: 'performance', well: '15_9-F-11_A' }

describe('Suggestions', () => {
  it('filters sessions by the current screen+well and excludes a given id', () => {
    render(<Suggestions sessions={INDEX} ctx={CTX} excludeId="s1" onPick={vi.fn()} />)
    expect(screen.queryByText('What drove the lost time?')).not.toBeInTheDocument()
    expect(screen.getByText('One-line lost-time number?')).toBeInTheDocument()
    expect(screen.queryByText('How is formation picked?')).not.toBeInTheDocument()
  })

  it('calls onPick with the session id and question on click', () => {
    const onPick = vi.fn()
    render(<Suggestions sessions={INDEX} ctx={CTX} onPick={onPick} />)
    fireEvent.click(screen.getByText('What drove the lost time?'))
    expect(onPick).toHaveBeenCalledWith('s1', 'What drove the lost time?')
  })

  it('renders nothing when there are no matches', () => {
    const { container } = render(
      <Suggestions sessions={INDEX} ctx={{ screen: 'trust' }} onPick={vi.fn()} />,
    )
    expect(container).toBeEmptyDOMElement()
  })
})
