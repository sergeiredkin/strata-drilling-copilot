import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeAll, describe, expect, it } from 'vitest'
import { axe } from 'vitest-axe'
import { installFixtureFetch } from '../../test/fixtureFetch'
import { useWells } from '../../data/hooks'
import { OffsetCompare } from './OffsetCompare'

beforeAll(() => {
  installFixtureFetch()
})

function Harness({ initialWellId }: { initialWellId?: string }) {
  const wells = useWells()
  if (!wells.data) return null
  return <OffsetCompare wells={wells.data.wells} initialWellId={initialWellId} />
}

function renderHarness(initialWellId?: string) {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(
    <QueryClientProvider client={client}>
      <Harness initialWellId={initialWellId} />
    </QueryClientProvider>,
  )
}

describe('OffsetCompare', () => {
  function pickerLabel(name: string): HTMLElement {
    // The picker checkboxes are the only place a well name sits inside a <label> -- a column
    // header (an unrelated <span>) also shows the same text once a well is selected.
    const label = screen
      .getAllByText(name)
      .map((el) => el.closest('label'))
      .find((l): l is HTMLLabelElement => l !== null)
    if (!label) throw new Error(`no picker <label> found for "${name}"`)
    return label
  }

  it('only offers wells that have a formations export as candidates', async () => {
    renderHarness()
    // Summary-only wells (e.g. 15/9-F-1 C) have no formations.json and must not appear as a
    // pickable checkbox, even though they're in the full well list.
    await waitFor(() => expect(pickerLabel('15/9-F-11 A')).toBeInTheDocument())
    expect(screen.queryByText('15/9-F-1 C')).not.toBeInTheDocument()
    expect(pickerLabel('15/9-F-5')).toBeInTheDocument()
    expect(pickerLabel('16A(78)-32')).toBeInTheDocument()
  })

  it('defaults to the current well plus one other, both rendered as columns', async () => {
    renderHarness('15_9-F-11_A')
    await waitFor(() => expect(screen.getAllByTitle(/Fm\.|GP\.|Overburden|Granitoid/).length).toBeGreaterThan(0))
    const checkboxes = screen.getAllByRole('checkbox', { checked: true })
    expect(checkboxes.length).toBe(2)
  })

  it('caps selection at 4 wells', async () => {
    const user = userEvent.setup()
    renderHarness('15_9-F-11_A')
    await waitFor(() => expect(pickerLabel('15/9-F-5')).toBeInTheDocument())
    // Only 3 detailed wells exist today, so capping at 4 can't be fully exercised here --
    // this at least confirms selecting every available candidate doesn't throw or drop state.
    for (const name of ['15/9-F-5', '16A(78)-32']) {
      const checkbox = within(pickerLabel(name)).getByRole('checkbox')
      if (!(checkbox as HTMLInputElement).checked) await user.click(checkbox)
    }
    expect(screen.getAllByRole('checkbox', { checked: true }).length).toBe(3)
  })

  it('toggling to True MD changes the alignment without crashing', async () => {
    const user = userEvent.setup()
    renderHarness('15_9-F-11_A')
    await waitFor(() => expect(screen.getByText('Flatten on tops')).toBeInTheDocument())
    await user.click(screen.getByRole('button', { name: 'True MD' }))
    expect(screen.getByRole('button', { name: 'True MD' })).toHaveAttribute('aria-pressed', 'true')
  })

  it('has no axe violations', async () => {
    const { container } = renderHarness('15_9-F-11_A')
    await waitFor(() => expect(pickerLabel('15/9-F-5')).toBeInTheDocument())
    const results = await axe(container)
    expect(results).toHaveNoViolations()
  })
})
