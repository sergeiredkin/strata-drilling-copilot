import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { useReplay } from '../../state/replay'
import { ReplayControls } from './ReplayControls'

beforeEach(() => {
  useReplay.getState().reset()
  useReplay.getState().setSpeed(1)
})

describe('ReplayControls', () => {
  it('shows "Replay" when paused and calls onPlay when clicked', async () => {
    const user = userEvent.setup()
    const onPlay = vi.fn()
    render(<ReplayControls onPlay={onPlay} onPause={vi.fn()} />)
    await user.click(screen.getByRole('button', { name: /Replay/ }))
    expect(onPlay).toHaveBeenCalledOnce()
  })

  it('shows "Pause" and calls onPause once playing', async () => {
    const user = userEvent.setup()
    const onPause = vi.fn()
    useReplay.getState().play()
    render(<ReplayControls onPlay={vi.fn()} onPause={onPause} />)
    await user.click(screen.getByRole('button', { name: /Pause/ }))
    expect(onPause).toHaveBeenCalledOnce()
  })

  it('changing speed updates the store', async () => {
    const user = userEvent.setup()
    render(<ReplayControls onPlay={vi.fn()} onPause={vi.fn()} />)
    await user.click(screen.getByRole('button', { name: '60×' }))
    expect(useReplay.getState().speed).toBe(60)
  })

  it('shows the time readout once t is set', () => {
    useReplay.getState().setT(Date.UTC(2013, 4, 20, 12, 0, 0))
    render(<ReplayControls onPlay={vi.fn()} onPause={vi.fn()} />)
    expect(screen.getByText('2013-05-20 12:00:00')).toBeInTheDocument()
  })

  it('toggling the event log shows alerts from the store', async () => {
    const user = userEvent.setup()
    useReplay.getState().pushLog({ type: 'alert', t: 0, alert: { id: 'a1', kind: 'data_gap', message: 'core gap' } })
    render(<ReplayControls onPlay={vi.fn()} onPause={vi.fn()} />)
    await user.click(screen.getByRole('button', { name: /Event log/ }))
    expect(screen.getByText('core gap')).toBeInTheDocument()
  })
})
