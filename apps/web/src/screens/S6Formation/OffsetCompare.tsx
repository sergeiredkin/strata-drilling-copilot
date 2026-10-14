// T11.4 offset compare — up to 4 wells side by side, aligned on real MD or flattened on tops
// (docs/06_SCREENS.md S6: "Offset compare: up to 4 wells side by side, aligned on formation
// tops (flattened) with a toggle to MD"). Only wells with a formations export can be picked —
// there's no hardcoded well-id list; candidacy is discovered by which `useFormationsForWells`
// queries actually resolve.
import { useMemo, useState } from 'react'
import type { WellSummary } from '../../contracts/types'
import { useFormationsForWells } from '../../data/hooks'
import { colorForFormation } from './depthScale'
import { buildFormationOrder, flattenBands, mdBands, type Band } from './offsetCompare'

const TRACK_HEIGHT = 480
const MAX_WELLS = 4

function BandColumn({ bands }: { bands: Band[] }) {
  return (
    <div style={{ position: 'relative', height: TRACK_HEIGHT }}>
      {bands.map((b) => (
        <div
          key={`${b.name}-${b.y0}`}
          title={b.name}
          className="absolute right-0 left-0 box-border overflow-hidden px-1.5 py-1"
          style={{ top: b.y0, height: Math.max(0, b.y1 - b.y0), background: colorForFormation(b.name) }}
        >
          <span className="text-[11px] font-semibold" style={{ color: '#0A0E13' }}>
            {b.name}
          </span>
        </div>
      ))}
    </div>
  )
}

export function OffsetCompare({ wells, initialWellId }: { wells: WellSummary[]; initialWellId?: string }) {
  const candidateIds = useMemo(() => wells.map((w) => w.id), [wells])
  const formationQueries = useFormationsForWells(candidateIds)
  const candidates = useMemo(
    () => wells.filter((_, i) => Boolean(formationQueries[i]?.data)),
    [wells, formationQueries],
  )

  const [manualSelection, setManualSelection] = useState<string[] | null>(null)
  const [mode, setMode] = useState<'md' | 'flatten'>('flatten')

  const defaultSelection = useMemo(() => {
    const ids = [initialWellId, ...candidates.map((c) => c.id)].filter(
      (id, i, arr): id is string => Boolean(id) && arr.indexOf(id) === i,
    )
    return ids.slice(0, 2)
  }, [candidates, initialWellId])

  const selected = manualSelection ?? defaultSelection

  function toggle(id: string) {
    const base = manualSelection ?? defaultSelection
    if (base.includes(id)) {
      setManualSelection(base.filter((x) => x !== id))
    } else if (base.length < MAX_WELLS) {
      setManualSelection([...base, id])
    }
  }

  const selectedWells = selected
    .map((id) => {
      const idx = candidateIds.indexOf(id)
      const summary = wells.find((w) => w.id === id)
      const report = formationQueries[idx]?.data
      return summary && report ? { summary, report } : null
    })
    .filter((x): x is { summary: WellSummary; report: NonNullable<(typeof formationQueries)[number]['data']> } =>
      Boolean(x),
    )

  const order = useMemo(
    () => buildFormationOrder(selectedWells.map((w) => w.report.tops)),
    [selectedWells],
  )
  const [mdMin, mdMax] = useMemo(() => {
    const tops = selectedWells.flatMap((w) => w.report.tops)
    if (tops.length === 0) return [0, 1]
    return [Math.min(...tops.map((t) => t.md_top)), Math.max(...tops.map((t) => t.md_base))]
  }, [selectedWells])

  return (
    <section className="flex flex-col gap-3 rounded border p-4" style={{ borderColor: 'var(--line)', background: 'var(--panel)' }}>
      <div className="flex flex-wrap items-center justify-between gap-3">
        <span className="font-condensed text-label uppercase text-text-3">Offset compare · up to 4 wells</span>
        <div className="flex gap-1.5">
          <button
            type="button"
            onClick={() => setMode('flatten')}
            aria-pressed={mode === 'flatten'}
            className="min-h-8 rounded border px-3 text-label"
            style={{ borderColor: mode === 'flatten' ? 'var(--accent)' : 'var(--line)', background: 'var(--panel-2)' }}
          >
            Flatten on tops
          </button>
          <button
            type="button"
            onClick={() => setMode('md')}
            aria-pressed={mode === 'md'}
            className="min-h-8 rounded border px-3 text-label"
            style={{ borderColor: mode === 'md' ? 'var(--accent)' : 'var(--line)', background: 'var(--panel-2)' }}
          >
            True MD
          </button>
        </div>
      </div>

      <div className="flex flex-wrap gap-1.5">
        {candidates.map((c) => (
          <label
            key={c.id}
            className="flex min-h-8 items-center gap-1.5 rounded border px-2.5 text-label"
            style={{ borderColor: selected.includes(c.id) ? 'var(--accent)' : 'var(--line)', background: 'var(--panel-2)' }}
          >
            <input
              type="checkbox"
              checked={selected.includes(c.id)}
              disabled={!selected.includes(c.id) && selected.length >= MAX_WELLS}
              onChange={() => toggle(c.id)}
            />
            {c.name}
          </label>
        ))}
      </div>

      {selectedWells.length === 0 ? (
        <p className="m-0 text-label text-text-2">Select at least one well with a formations export above.</p>
      ) : (
        <div className="flex flex-wrap gap-3 overflow-x-auto">
          {selectedWells.map(({ summary, report }) => (
            <div key={summary.id} className="min-w-[160px] flex-1">
              <div className="mb-1.5 flex items-baseline justify-between gap-2">
                <span className="font-mono text-dense">{summary.name}</span>
                {summary.is_mock && (
                  <span className="font-mono text-label" style={{ color: 'var(--mock-fg)' }}>
                    mock
                  </span>
                )}
              </div>
              <BandColumn
                bands={
                  mode === 'md'
                    ? mdBands(report.tops, mdMin, mdMax, TRACK_HEIGHT)
                    : flattenBands(report.tops, order, TRACK_HEIGHT)
                }
              />
            </div>
          ))}
        </div>
      )}
      <p className="m-0 text-label text-text-2">
        Flatten on tops normalises every formation to an equal-height row so the same name lines up across wells —
        it is a correlation aid, not a depth scale. True MD keeps each well's own real depth.
      </p>
    </section>
  )
}
