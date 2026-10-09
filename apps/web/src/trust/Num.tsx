// docs/05_DESIGN_SYSTEM.md §6: hover/focus opens <EvidencePopover id>; verified === false -> red
// solid underline on red-tinted bg + "✕ not verified" in the popover; missing evidence_id ->
// dev-only console.error. "A number without evidence is a bug" (01_PRODUCT_SPEC.md).
import {
  FloatingPortal,
  flip,
  offset,
  shift,
  useDismiss,
  useFloating,
  useFocus,
  useHover,
  useInteractions,
  useRole,
} from '@floating-ui/react'
import { useState } from 'react'
import type { Quantity } from '../contracts/types'
import { usePrefs } from '../state/prefs'
import { formatQuantity } from '../units/format'
import { EvidencePopover } from './EvidencePopover'

export type NumProps = {
  q: Quantity
  kind?: 'inline' | 'kpi'
  showUnit?: boolean
  /** Only meaningful when `q` backs a copilot Claim — undefined means "not applicable". */
  verified?: boolean
  verifyNote?: string
}

export function Num({ q, kind = 'inline', showUnit = true, verified, verifyNote }: NumProps) {
  const units = usePrefs((s) => s.units)
  const [open, setOpen] = useState(false)

  if (import.meta.env.DEV && !q.evidence_id) {
    console.error('<Num> rendered without an evidence_id — a number without evidence is a bug.', q)
  }

  const { refs, floatingStyles, context } = useFloating({
    open,
    onOpenChange: setOpen,
    placement: 'bottom-start',
    middleware: [offset(6), flip(), shift({ padding: 8 })],
  })

  const hover = useHover(context, { move: false })
  const focus = useFocus(context)
  const dismiss = useDismiss(context)
  const role = useRole(context, { role: 'dialog' })
  const { getReferenceProps, getFloatingProps } = useInteractions([hover, focus, dismiss, role])

  const formatted = formatQuantity(q, units)
  const isUnverified = verified === false

  return (
    <>
      <button
        type="button"
        ref={refs.setReference}
        {...getReferenceProps()}
        className={[
          'cursor-default rounded-sm font-mono tabular-nums',
          kind === 'kpi' ? 'text-well-id font-semibold' : 'text-dense',
          isUnverified ? 'underline decoration-2' : 'border-b border-dashed',
        ].join(' ')}
        style={{
          color: 'inherit',
          borderColor: isUnverified ? undefined : 'var(--link)',
          textDecorationColor: isUnverified ? 'var(--danger)' : undefined,
          background: isUnverified ? 'color-mix(in srgb, var(--danger) 12%, transparent)' : undefined,
        }}
      >
        {showUnit ? formatted.display : formatted.text}
      </button>
      {open && (
        <FloatingPortal>
          <div
            ref={refs.setFloating}
            style={{
              ...floatingStyles,
              background: 'var(--panel)',
              border: '1px solid var(--line)',
              borderRadius: 6,
              zIndex: 50,
            }}
            {...getFloatingProps()}
          >
            <EvidencePopover id={q.evidence_id} verified={verified} verifyNote={verifyNote} />
          </div>
        </FloatingPortal>
      )}
    </>
  )
}
