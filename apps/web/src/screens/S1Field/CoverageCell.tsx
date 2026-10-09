// One of the 6 coverage cells — docs/05_DESIGN_SYSTEM.md §5 (full/partial/none, 52x26px) and
// 06_SCREENS.md S1 ("coverage cell hover -> rows, date span, source files").
import { useId } from 'react'
import type { CoverageCell as CoverageCellType } from '../../contracts/types'

const GLYPH: Record<CoverageCellType['status'], string> = {
  full: '●',
  partial: '◐',
  none: '○',
}

function describeSpan(span: CoverageCellType['span']): string {
  if (!span) return 'no date span recorded'
  const [t0, t1] = span
  return `${new Date(t0).toISOString().slice(0, 10)} → ${new Date(t1).toISOString().slice(0, 10)}`
}

export function CoverageCell({ cell }: { cell: CoverageCellType }) {
  const descId = useId()
  const tooltip = [
    cell.rows !== null ? `${cell.rows} rows` : 'row count unknown',
    describeSpan(cell.span),
    cell.source_files && cell.source_files.length > 0 ? cell.source_files.join(', ') : 'no source file recorded',
  ].join(' · ')

  return (
    <button
      type="button"
      className="group relative inline-flex h-[26px] w-[52px] items-center justify-center rounded text-dense"
      style={
        cell.status === 'full'
          ? { background: '#2E7D5B', color: '#E8FFF4' }
          : cell.status === 'partial'
            ? {
                background:
                  'repeating-linear-gradient(45deg, #8A6A1F 0 3px, #3A2F16 3px 6px)',
                color: '#FFE7B0',
              }
            : { background: 'var(--panel-2)', border: '1px solid var(--line)', color: 'var(--text-3)' }
      }
      aria-describedby={descId}
      title={`${cell.status} — ${tooltip}`}
    >
      {GLYPH[cell.status]}
      <span
        id={descId}
        role="tooltip"
        className="pointer-events-none absolute left-1/2 top-full z-10 mt-1 w-max max-w-72 -translate-x-1/2 whitespace-normal rounded border p-2 text-left text-label opacity-0 shadow-lg group-hover:opacity-100 group-focus-visible:opacity-100"
        style={{ background: 'var(--panel)', borderColor: 'var(--line)', color: 'var(--text-2)' }}
      >
        {tooltip}
      </span>
    </button>
  )
}
