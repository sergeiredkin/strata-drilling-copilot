// Always-visible legend under the ribbon — docs/05_DESIGN_SYSTEM.md §3 ("A legend is always
// visible under the ribbon"). Plain HTML swatches (not canvas) since this never needs to scroll/
// zoom with the tracks.
import { RIG_STATE_LABEL, RIG_STATE_ORDER } from '../plugins/rigStateStyle'

const STRIPE_CSS: Partial<Record<string, string>> = {
  sliding: 'repeating-linear-gradient(135deg, var(--state-sliding-stripe) 0 4px, var(--state-sliding-fill) 4px 8px)',
  trip_in: 'repeating-linear-gradient(90deg, var(--state-trip-in-stripe) 0 4px, var(--state-trip-in-fill) 4px 8px)',
  reaming: 'repeating-linear-gradient(90deg, var(--state-reaming-stripe) 0 3px, var(--state-reaming-fill) 3px 6px)',
}

export function RigStateLegend() {
  return (
    <div className="flex flex-wrap gap-x-4 gap-y-2 text-meta text-text-2">
      {RIG_STATE_ORDER.map((state) => (
        <span key={state} className="inline-flex items-center gap-1.5">
          <span
            className="inline-block h-[12px] w-[22px] rounded-sm"
            style={{ background: STRIPE_CSS[state] ?? `var(--state-${state.replace(/_/g, '-')}-fill)` }}
          />
          {RIG_STATE_LABEL[state]}
        </span>
      ))}
    </div>
  )
}
