import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import { beforeAll, beforeEach, describe, expect, it } from 'vitest'
import { axe } from 'vitest-axe'
import { installFixtureFetch } from '../../test/fixtureFetch'
import { EMPTY_VIEW_STATE, useView } from '../../state/view'
import { S1Field } from './S1Field'

beforeAll(() => {
  installFixtureFetch()
})

function renderScreen() {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(
    <QueryClientProvider client={client}>
      <MemoryRouter>
        <S1Field />
      </MemoryRouter>
    </QueryClientProvider>,
  )
}

describe('S1Field', () => {
  beforeEach(() => {
    useView.getState().replaceState(EMPTY_VIEW_STATE)
  })

  it('renders all 9 wells', async () => {
    renderScreen()
    await waitFor(() => expect(screen.getByText('15/9-F-11 A')).toBeInTheDocument())
    for (const name of ['15/9-F-1 C', '15/9-F-12', '15/9-F-14', '15/9-F-15 D', '15/9-F-5', '16A(78)-32', '16B(78)-32', '58-32']) {
      expect(screen.getByText(name)).toBeInTheDocument()
    }
  })

  it('search filters the table live', async () => {
    const user = userEvent.setup()
    renderScreen()
    await waitFor(() => expect(screen.getByText('15/9-F-11 A')).toBeInTheDocument())

    await user.type(screen.getByLabelText('Search'), 'F-5')
    await waitFor(() => expect(screen.queryByText('15/9-F-11 A')).not.toBeInTheDocument())
    expect(screen.getByText('15/9-F-5')).toBeInTheDocument()
  })

  it('the Volve field chip filters out FORGE wells', async () => {
    const user = userEvent.setup()
    renderScreen()
    await waitFor(() => expect(screen.getByText('16A(78)-32')).toBeInTheDocument())

    await user.click(screen.getByRole('button', { name: 'Volve' }))
    await waitFor(() => expect(screen.queryByText('16A(78)-32')).not.toBeInTheDocument())
    expect(screen.getByText('15/9-F-11 A')).toBeInTheDocument()
  })

  it('has no axe violations', async () => {
    const { container } = renderScreen()
    await waitFor(() => expect(screen.getByText('15/9-F-11 A')).toBeInTheDocument())
    const results = await axe(container)
    expect(results).toHaveNoViolations()
  })
})
