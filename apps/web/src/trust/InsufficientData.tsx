// docs/05_DESIGN_SYSTEM.md §9: "empty states say what is missing and why." Used wherever a
// tool/screen has nothing to show instead of silently rendering a blank area.
import { ConfidenceBadge } from './ConfidenceBadge'

export function InsufficientData({ reason }: { reason: string }) {
  return (
    <div
      className="flex items-start gap-2 rounded border p-3 text-dense"
      style={{ borderColor: 'var(--line)', background: 'var(--panel-2)', color: 'var(--text-2)' }}
    >
      <ConfidenceBadge c={{ level: 'insufficient', reason }} />
      <p className="m-0">{reason}</p>
    </div>
  )
}
