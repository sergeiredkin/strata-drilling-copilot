import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'
import type { ReplayEvent } from '../../contracts/types'
import { ReplayLog } from './ReplayLog'

describe('ReplayLog', () => {
  it('shows an honest empty state with no alerts', () => {
    render(<ReplayLog log={[]} onClose={vi.fn()} />)
    expect(screen.getByText('No alerts yet this session.')).toBeInTheDocument()
  })

  it('lists only alert events, not state transitions', () => {
    const log: ReplayEvent[] = [
      { type: 'state', t: 0, state: 'rotary_drilling' },
      { type: 'alert', t: 1000, alert: { id: 'a1', kind: 'flat_time', message: 'Flat time 20 min' } },
    ]
    render(<ReplayLog log={log} onClose={vi.fn()} />)
    expect(screen.getByText('Flat time 20 min')).toBeInTheDocument()
    expect(screen.queryByText('No alerts yet this session.')).not.toBeInTheDocument()
  })

  it('calls onClose when the close button is clicked', async () => {
    const user = userEvent.setup()
    const onClose = vi.fn()
    render(<ReplayLog log={[]} onClose={onClose} />)
    await user.click(screen.getByRole('button', { name: 'Close event log' }))
    expect(onClose).toHaveBeenCalledOnce()
  })
})
