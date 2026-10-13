import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { beforeAll, describe, expect, it } from 'vitest'
import { axe } from 'vitest-axe'
import { installFixtureFetch } from '../../test/fixtureFetch'
import { S6Formation } from './S6Formation'

beforeAll(() => {
  installFixtureFetch()
})

function renderAt(path: string) {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(
    <QueryClientProvider client={client}>
      <MemoryRouter initialEntries={[path]}>
        <Routes>
          <Route path="well/:id/formation" element={<S6Formation />} />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>,
  )
}

describe('S6Formation', () => {
  it('renders the real wells tops, curve tracks and per-formation table', async () => {
    renderAt('/well/15_9-F-11_A/formation')
    await waitFor(() => expect(screen.getByText('15/9-F-11 A')).toBeInTheDocument())
    expect(screen.getByText('Per-formation summary')).toBeInTheDocument()
    // At least one real formation name from the real tops export should appear in the tops track.
    expect(screen.getAllByText(/Fm\.|GP\.|Hugin|Draupne|Ty|Ekofisk|Hod|Heather|Utsira/).length).toBeGreaterThan(0)
  })

  it('shows "no trained prediction" for the real well (LOWO still blocked)', async () => {
    renderAt('/well/15_9-F-11_A/formation')
    await waitFor(() => expect(screen.getByText('15/9-F-11 A')).toBeInTheDocument())
    expect(screen.getByText('No trained prediction for this well yet.')).toBeInTheDocument()
  })

  it('renders a mock detailed well with its MOCK badge and a predicted track', async () => {
    renderAt('/well/15_9-F-5/formation')
    await waitFor(() => expect(screen.getByText('15/9-F-5')).toBeInTheDocument())
    expect(screen.getByText('Mock')).toBeInTheDocument()
    expect(screen.queryByText('No trained prediction for this well yet.')).not.toBeInTheDocument()
  })

  it('shows insufficient data for a summary-only well (no dense series)', async () => {
    renderAt('/well/15_9-F-1_C/formation')
    await waitFor(() =>
      expect(screen.getAllByText(/has no formation\/depth-series export yet/).length).toBeGreaterThan(0),
    )
  })

  it('shows insufficient data for an unknown well id', async () => {
    renderAt('/well/not-a-real-well/formation')
    await waitFor(() => expect(screen.getAllByText(/No well named/).length).toBeGreaterThan(0))
  })

  it('has no axe violations', async () => {
    const { container } = renderAt('/well/15_9-F-11_A/formation')
    await waitFor(() => expect(screen.getByText('Per-formation summary')).toBeInTheDocument())
    const results = await axe(container)
    expect(results).toHaveNoViolations()
  })
})
