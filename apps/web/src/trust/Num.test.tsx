import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeAll, beforeEach, describe, expect, it, vi } from 'vitest'
import type { Quantity } from '../contracts/types'
import { installFixtureFetch } from '../test/fixtureFetch'
import { Num } from './Num'

beforeAll(() => {
  installFixtureFetch()
})

function renderWithQuery(ui: React.ReactElement) {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(<QueryClientProvider client={client}>{ui}</QueryClientProvider>)
}

// A real evidence id + params from the committed fixtures (wells.json's first well's qc_score).
const REAL_QC_SCORE: Quantity = { value: 0.91, unit: '1', evidence_id: 'ev_a8006fed4f', precision: 2 }

describe('Num + EvidencePopover', () => {
  beforeEach(() => {
    localStorage.clear()
  })

  it('opens the popover on hover with tool, params and sources', async () => {
    const user = userEvent.setup()
    renderWithQuery(<Num q={REAL_QC_SCORE} />)

    const trigger = screen.getByRole('button')
    await user.hover(trigger)

    await waitFor(() => expect(screen.getByText('qc.score')).toBeInTheDocument())
    expect(screen.getByText(/"well":"15_9-F-11_A"/)).toBeInTheDocument()
    expect(screen.getByText(/fixtures\/wells\.py/)).toBeInTheDocument()
  })

  it('opens the popover on keyboard focus (Tab)', async () => {
    const user = userEvent.setup()
    renderWithQuery(<Num q={REAL_QC_SCORE} />)

    await user.tab()
    expect(screen.getByRole('button')).toHaveFocus()
    await waitFor(() => expect(screen.getByText('qc.score')).toBeInTheDocument())
  })

  it('Escape closes the popover', async () => {
    const user = userEvent.setup()
    renderWithQuery(<Num q={REAL_QC_SCORE} />)

    await user.tab()
    await waitFor(() => expect(screen.getByText('qc.score')).toBeInTheDocument())
    await user.keyboard('{Escape}')
    await waitFor(() => expect(screen.queryByText('qc.score')).not.toBeInTheDocument())
  })

  it('shows the value in both unit systems', async () => {
    const q: Quantity = { value: 100, unit: 'bar', evidence_id: 'ev_a8006fed4f', precision: 1 }
    const user = userEvent.setup()
    renderWithQuery(<Num q={q} />)

    await user.hover(screen.getByRole('button'))
    await waitFor(() => expect(screen.getByText('qc.score')).toBeInTheDocument())
    // EvidencePopover shows the evidence record's own value/unit (0.91 / "1"), converted both
    // ways — the parenthetical "(x unit / y unit)" form.
    expect(screen.getByText(/\(.*\/.*\)/)).toBeInTheDocument()
  })

  it('renders unverified styling and the "not verified" note', async () => {
    const user = userEvent.setup()
    renderWithQuery(<Num q={REAL_QC_SCORE} verified={false} verifyNote="evidence says something else" />)

    const trigger = screen.getByRole('button')
    expect(trigger.className).toContain('underline')

    await user.hover(trigger)
    await waitFor(() => expect(screen.getByText(/not verified/)).toBeInTheDocument())
    expect(screen.getByText(/evidence says something else/)).toBeInTheDocument()
  })

  it('shows a readable error for a missing evidence record', async () => {
    const q: Quantity = { value: 1, unit: 'kN', evidence_id: 'ev_0000000000' }
    const user = userEvent.setup()
    renderWithQuery(<Num q={q} />)

    await user.hover(screen.getByRole('button'))
    await waitFor(() => expect(screen.getByText(/No evidence record/)).toBeInTheDocument())
  })

  it('logs a dev console.error when evidence_id is missing', () => {
    const spy = vi.spyOn(console, 'error').mockImplementation(() => undefined)
    const q = { value: 1, unit: 'kN', evidence_id: '' } as unknown as Quantity
    renderWithQuery(<Num q={q} />)
    expect(spy).toHaveBeenCalledWith(expect.stringContaining('without an evidence_id'), q)
    spy.mockRestore()
  })
})
