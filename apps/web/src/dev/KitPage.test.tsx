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

    // wait for the wells.json-backed Num examples to resolve past the loading state
    await waitFor(() => expect(getAllByText('0.91').length).toBeGreaterThan(0))

    const results = await axe(container)
    expect(results).toHaveNoViolations()
  })
})
