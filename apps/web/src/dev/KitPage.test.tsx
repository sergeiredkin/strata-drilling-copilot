import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, waitFor } from '@testing-library/react'
import { beforeAll, describe, expect, it } from 'vitest'
import { axe } from 'vitest-axe'
import { installFixtureFetch } from '../test/fixtureFetch'
import { KitPage } from './KitPage'

beforeAll(() => {
  installFixtureFetch()
})

describe('/dev/kit accessibility', () => {
  it('has no axe violations', async () => {
    const client = new QueryClient({ defaultOptions: { queries: { retry: false } } })
    const { container, getAllByText } = render(
      <QueryClientProvider client={client}>
        <KitPage />
      </QueryClientProvider>,
    )

    // wait for the wells.json-backed Num examples (firstWell.qc_score) to resolve past the
    // loading state — not the exact value, which depends on which well sorts first in the
    // committed export (T10.4 moved 15_9-F-11_A to real data, which generate_real appends
    // after the mock wells, changing which well is first).
    await waitFor(() => expect(getAllByText(/^\d\.\d\d$/).length).toBeGreaterThan(0))

    const results = await axe(container)
    expect(results).toHaveNoViolations()
  })
})
