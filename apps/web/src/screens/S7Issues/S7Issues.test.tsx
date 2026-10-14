import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { beforeAll, beforeEach, describe, expect, it } from 'vitest'
import { axe } from 'vitest-axe'
import { installFixtureFetch } from '../../test/fixtureFetch'
import { EMPTY_VIEW_STATE, useView } from '../../state/view'
import { S7Issues } from './S7Issues'

beforeAll(() => {
  installFixtureFetch()
})

beforeEach(() => {
  useView.getState().replaceState(EMPTY_VIEW_STATE)
})

function renderAt(path = '/issues') {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(
    <QueryClientProvider client={client}>
      <MemoryRouter initialEntries={[path]}>
        <Routes>
          <Route path="issues" element={<S7Issues />} />
          <Route path="well/:id/workspace" element={<div data-testid="workspace-landed" />} />
          <Route path="well/:id/formation" element={<div data-testid="formation-landed" />} />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>,
  )
}

describe('S7Issues', () => {
  it('lists the real extracted issues with well names resolved', async () => {
    renderAt()
    await waitFor(() => expect(screen.getAllByText('15/9-F-11 A').length).toBeGreaterThan(0))
    expect(screen.getByText('Formation × type counts')).toBeInTheDocument()
  })

  it('"Excerpt" expands the DDR narrative for that row', async () => {
    const user = userEvent.setup()
    renderAt()
    await waitFor(() => expect(screen.getAllByText('15/9-F-11 A').length).toBeGreaterThan(0))
    await user.click(screen.getAllByRole('button', { name: 'Excerpt' })[0] as HTMLElement)
    expect(screen.getByText(/DDR 2013-/)).toBeInTheDocument()
  })

  it('"Open in Workspace" navigates to the well workspace at the issue window', async () => {
    const user = userEvent.setup()
    renderAt()
    await waitFor(() => expect(screen.getAllByText('15/9-F-11 A').length).toBeGreaterThan(0))
    await user.click(screen.getAllByRole('button', { name: 'Open in Workspace' })[0] as HTMLElement)
    await waitFor(() => expect(screen.getByTestId('workspace-landed')).toBeInTheDocument())
  })

  it('"Open in Formation" navigates to the well formation screen', async () => {
    const user = userEvent.setup()
    renderAt()
    await waitFor(() => expect(screen.getAllByText('15/9-F-11 A').length).toBeGreaterThan(0))
    await user.click(screen.getAllByRole('button', { name: 'Open in Formation' })[0] as HTMLElement)
    await waitFor(() => expect(screen.getByTestId('formation-landed')).toBeInTheDocument())
  })

  it('filtering by well=a-well-with-no-issues shows the honest empty state', async () => {
    // The URL<->store sync (useViewUrlSync) only runs inside Shell in production; this test
    // sets the filter directly on the store, same as what that sync would do for ?well=...
    useView.getState().setFilter('well', '15_9-F-5')
    renderAt()
    await waitFor(() =>
      expect(screen.getByText(/No issues match these filters/)).toBeInTheDocument(),
    )
  })

  it('has no axe violations', async () => {
    const { container } = renderAt()
    await waitFor(() => expect(screen.getAllByText('15/9-F-11 A').length).toBeGreaterThan(0))
    const results = await axe(container)
    expect(results).toHaveNoViolations()
  })
})
