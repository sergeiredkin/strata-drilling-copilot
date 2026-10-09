import { fireEvent, render, screen } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import type { ReproManifest } from '../../contracts/types'
import { ReproducePanel } from './ReproducePanel'

const MANIFEST: ReproManifest = {
  git_commit: 'abcdef1234567890',
  data_files: [{ path: 'a.json', sha256: 'x' }, { path: 'b.json', sha256: 'y' }],
  command: 'make fixtures',
  generated_at: '2026-01-01T00:00:00Z',
}

describe('ReproducePanel', () => {
  it('shows the reproduce command for this well', () => {
    render(<ReproducePanel manifest={MANIFEST} wellId="15_9-F-11_A" />)
    expect(screen.getByText(/make reproduce WELL=15_9-F-11_A/)).toBeInTheDocument()
    expect(screen.getByText(/2 files/)).toBeInTheDocument()
  })

  it('copies the reproduce command to the clipboard on click', async () => {
    const writeText = vi.fn().mockResolvedValue(undefined)
    Object.assign(navigator, { clipboard: { writeText } })

    render(<ReproducePanel manifest={MANIFEST} wellId="15_9-F-11_A" />)
    fireEvent.click(screen.getByRole('button', { name: 'Copy command' }))

    expect(writeText).toHaveBeenCalledWith('make reproduce WELL=15_9-F-11_A')
    expect(await screen.findByText('Copied!')).toBeInTheDocument()
  })
})
