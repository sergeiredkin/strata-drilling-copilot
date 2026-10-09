// Exercises the T8.2 "context handoff" path: another screen (S2's mismatch popover) sets
// view.copilotPrefill + opens the panel, and the dock must auto-ask it and clear the prefill —
// against the real fixtures via installFixtureFetch, not a mock DataSource.
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { beforeAll, beforeEach, describe, expect, it } from 'vitest'
import { installFixtureFetch } from '../test/fixtureFetch'
import { EMPTY_VIEW_STATE, useView } from '../state/view'
import { CopilotDock } from './CopilotDock'

beforeAll(() => {
  installFixtureFetch()
})

beforeEach(() => {
  useView.getState().replaceState(EMPTY_VIEW_STATE)
})

function renderDock(initialPath: string) {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(
    <QueryClientProvider client={client}>
      <MemoryRouter initialEntries={[initialPath]}>
        <CopilotDock />
      </MemoryRouter>
    </QueryClientProvider>,
  )
}

describe('CopilotDock', () => {
  it('renders nothing when the panel is closed', () => {
    renderDock('/well/15_9-F-11_A/workspace')
    expect(screen.queryByLabelText('Copilot')).not.toBeInTheDocument()
  })

  it('auto-asks a prefilled question on open and clears the prefill', async () => {
    useView.getState().setCopilotPrefill('Why does the sensor data say Trip out here?')
    useView.getState().setPanel('copilot')

    renderDock('/well/15_9-F-11_A/workspace')

    expect(screen.getByText('Why does the sensor data say Trip out here?')).toBeInTheDocument()
    await waitFor(() => expect(screen.getByText('Live mode required')).toBeInTheDocument())
    expect(useView.getState().copilotPrefill).toBeNull()
  })

  it('asks a recorded session from the URL (?s=) and renders its AnswerCard', async () => {
    useView.getState().setPanel('copilot')
    useView.getState().setSessionId('s1_ilt_breakdown')

    renderDock('/well/15_9-F-11_A/performance')

    await waitFor(
      () => expect(screen.getByText(/invisible lost time totals 15.0 h/)).toBeInTheDocument(),
      { timeout: 3000 },
    )
  })
})
