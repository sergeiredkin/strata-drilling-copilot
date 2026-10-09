import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import type { CopilotContext } from '../contracts/types'
import { ContextLine } from './ContextLine'

describe('ContextLine', () => {
  it('shows "no well selected" when the context has no well', () => {
    render(<ContextLine ctx={{ screen: 'field' }} />)
    expect(screen.getByText(/no well selected/)).toBeInTheDocument()
  })

  it('shows well, section, time window and depth window when all are present', () => {
    const ctx: CopilotContext = {
      screen: 'performance',
      well: '15_9-F-11_A',
      section: '12 1/4',
      time_window: [1717200000000, 1717203600000],
      depth_window: [2455, 2500],
    }
    render(<ContextLine ctx={ctx} />)
    const text = screen.getByText(/context ·/).textContent ?? ''
    expect(text).toContain('15_9-F-11_A')
    expect(text).toContain('12 1/4')
    expect(text).toContain('2455–2500 m')
  })

  it('omits section/window/depth parts that are absent', () => {
    render(<ContextLine ctx={{ screen: 'workspace', well: '15_9-F-11_A' }} />)
    const text = screen.getByText(/context ·/).textContent ?? ''
    expect(text).toBe('context · 15_9-F-11_A')
  })
})
