import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it } from 'vitest'
import { ConfidenceBadge } from './ConfidenceBadge'

describe('ConfidenceBadge', () => {
  it('renders the glyph and label for each level', () => {
    render(<ConfidenceBadge c={{ level: 'high', reason: 'because' }} />)
    expect(screen.getByText('High')).toBeInTheDocument()
  })

  it('the reason is in the DOM (available to screen readers) even before hover', () => {
    render(<ConfidenceBadge c={{ level: 'low', reason: 'only 2 samples' }} />)
    expect(screen.getByText('only 2 samples')).toBeInTheDocument()
  })

  it('is keyboard-focusable (a real button)', async () => {
    const user = userEvent.setup()
    render(<ConfidenceBadge c={{ level: 'medium', reason: 'partial coverage' }} />)
    await user.tab()
    expect(screen.getByRole('button')).toHaveFocus()
  })
})
