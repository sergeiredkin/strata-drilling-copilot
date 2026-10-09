// S2 Well workspace — docs/06_SCREENS.md S2, comp docs/design/comps/S2-Workspace.dc.html.
import { useEffect, useMemo, useRef, useState } from 'react'
import { useParams } from 'react-router-dom'
import { DdrLaneTrack } from '../../charts/TrackStack/DdrLaneTrack'
import { DepthTime } from '../../charts/DepthTime/DepthTime'
import { Overview } from '../../charts/DepthTime/Overview'
import { RIG_STATE_LABEL } from '../../charts/plugins/rigStateStyle'
import { RibbonTrack } from '../../charts/TrackStack/RibbonTrack'
import { RigStateLegend } from '../../charts/TrackStack/RigStateLegend'
import { clampRange } from '../../charts/TrackStack/axes'
import { createTimeRangeSync } from '../../charts/TrackStack/sync'
import { TrackStack, type TrackDef } from '../../charts/TrackStack/TrackStack'
import { useDdr, useMismatches, useRigState, useSections, useWells } from '../../data/hooks'
import { useView } from '../../state/view'
import { ConfidenceBadge } from '../../trust/ConfidenceBadge'
import { InsufficientData } from '../../trust/InsufficientData'
import { MockBadge } from '../../trust/MockBadge'
import { MismatchPopover } from './MismatchPopover'

const TRACKS: TrackDef[] = [
  { channel: 'HKLD', name: 'Hookload' },
  { channel: 'WOB', name: 'WOB' },
  { channel: 'RPM', name: 'RPM' },
  { channel: 'TORQ', name: 'Torque' },
  { channel: 'SPP', name: 'SPP' },
  { channel: 'FLOWIN', name: 'Flow in' },
]

const TRACK_UNITS = { HKLD: 'kN', WOB: 'kN', RPM: 'rpm', TORQ: 'kN.m', SPP: 'bar', FLOWIN: 'L/min' }
const ZOOM_FACTOR = 0.6

function breadcrumbLabel(windowMs: number): string {
  const min = windowMs / 60_000
  if (min < 90) return `${min.toFixed(0)} min window`
  const h = min / 60
  if (h < 48) return `${h.toFixed(1)} h window`
  return `${(h / 24).toFixed(1)} day window`
}

export function S2Workspace() {
  const { id: wellId } = useParams<{ id: string }>()
  const timeRange = useView((s) => s.timeRange)
  const setTimeRange = useView((s) => s.setTimeRange)
  const setPanel = useView((s) => s.setPanel)
  const setCopilotPrefill = useView((s) => s.setCopilotPrefill)

  const wells = useWells()
  const wellSummary = wells.data?.wells.find((w) => w.id === wellId)
  const sections = useSections(wellId)
  const firstSection = sections.data?.[0]
  const lastSection = sections.data?.at(-1)
  const fullRange: [number, number] | null =
    firstSection && lastSection ? [firstSection.t_start, lastSection.t_end] : null
  const fullRangeStart = fullRange?.[0]
  const fullRangeEnd = fullRange?.[1]

  const sync = useMemo(
    () => createTimeRangeSync(fullRangeStart !== undefined && fullRangeEnd !== undefined ? [fullRangeStart, fullRangeEnd] : [0, 1]),
    [fullRangeStart, fullRangeEnd],
  )
  const [range, setRange] = useState<[number, number]>(fullRange ?? [0, 1])
  const rangeRef = useRef(range)
  rangeRef.current = range

  // fullRange resolves async (sections() fetch); once it does (or the well changes), snap the
  // working range to the URL's t0/t1 if present, else the full well. Runs in an effect, not
  // during render, since it has the side effect of publishing to `sync`.
  useEffect(() => {
    if (!fullRange) return
    const initial = clampRange(
      (timeRange ?? fullRange)[0],
      (timeRange ?? fullRange)[1],
      fullRange[0],
      fullRange[1],
    )
    sync.setRange(initial)
    setRange(initial)
    // Deliberately excludes `timeRange`: this effect seeds the range once per well/fullRange
    // resolution, it doesn't re-snap every time the URL changes (zoom/pan already does that
    // through handleRangeSettled).
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [fullRangeStart, fullRangeEnd, sync])

  const effectiveRange = fullRange ? range : null

  const rigState = useRigState(wellId, effectiveRange?.[0] ?? 0, effectiveRange?.[1] ?? 0)
  const ddr = useDdr(wellId, effectiveRange?.[0] ?? 0, effectiveRange?.[1] ?? 0)
  const mismatches = useMismatches(wellId)
  const [openMismatchId, setOpenMismatchId] = useState<string | null>(null)
  const openMismatch = mismatches.data?.find((m) => m.id === openMismatchId) ?? null
  const openDdrRow = openMismatch ? ddr.data?.find((r) => r.id === openMismatch.ddr_activity_id) : undefined

  function handleRangeSettled(next: [number, number]) {
    setRange(next)
    setTimeRange(next)
  }

  function zoom(factor: number) {
    if (!fullRange) return
    const [t0, t1] = rangeRef.current
    const mid = (t0 + t1) / 2
    const halfWidth = ((t1 - t0) * factor) / 2
    const next = clampRange(mid - halfWidth, mid + halfWidth, fullRange[0], fullRange[1])
    sync.setRange(next)
    handleRangeSettled(next)
  }

  function fitConnection() {
    if (!rigState.data || rigState.data.length === 0 || !fullRange) return
    const [t0, t1] = rangeRef.current
    const mid = (t0 + t1) / 2
    const nearest = rigState.data
      .filter((iv) => iv.state === 'connection')
      .reduce<{ t0: number; t1: number } | null>((best, iv) => {
        const ivMid = (iv.t0 + iv.t1) / 2
        if (!best || Math.abs(ivMid - mid) < Math.abs((best.t0 + best.t1) / 2 - mid)) return iv
        return best
      }, null)
    if (!nearest) return
    const padded = clampRange(nearest.t0 - 2 * 60_000, nearest.t1 + 2 * 60_000, fullRange[0], fullRange[1])
    sync.setRange(padded)
    handleRangeSettled(padded)
  }

  if (!wellId) return <InsufficientData reason="No well selected." />

  if (wells.isLoading || sections.isLoading) {
    return <div className="p-6 text-text-2">Loading…</div>
  }

  if (!wellSummary) {
    return <InsufficientData reason={`No well named "${wellId}" was found in this export.`} />
  }

  if (!fullRange || !effectiveRange) {
    return (
      <div className="p-6">
        <InsufficientData
          reason={`${wellSummary.name} has no detail time-series export yet — only summary data is available on S1.`}
        />
      </div>
    )
  }

  const section = sections.data?.[0]
  const windowMs = effectiveRange[1] - effectiveRange[0]

  return (
    <div className="flex min-h-0 flex-1 flex-wrap">
      <main className="flex min-w-0 flex-[999_1_760px] flex-col gap-3.5 px-5 py-4.5">
        <div className="flex flex-wrap items-center gap-x-4.5 gap-y-2.5">
          <h1 className="m-0 font-mono text-well-id">{wellSummary.name}</h1>
          <ConfidenceBadge c={wellSummary.confidence} />
          <nav className="flex flex-wrap items-center gap-1.5 text-dense text-text-2">
            <button type="button" onClick={() => zoom(100)} className="text-text-2 hover:text-link">
              Full well
            </button>
            <span>{'›'}</span>
            <span>{section ? `${section.size_in}″ section` : 'section'}</span>
            <span>{'›'}</span>
            <span className="text-text">{breadcrumbLabel(windowMs)}</span>
          </nav>
          <div className="ml-auto flex flex-wrap items-center gap-1.5">
            <button
              type="button"
              aria-label="Zoom out"
              onClick={() => zoom(1 / ZOOM_FACTOR)}
              className="min-h-9 rounded border px-3 text-dense"
              style={{ borderColor: 'var(--line)', background: 'var(--panel)' }}
            >
              {'−'}
            </button>
            <button
              type="button"
              aria-label="Zoom in"
              onClick={() => zoom(ZOOM_FACTOR)}
              className="min-h-9 rounded border px-3 text-dense"
              style={{ borderColor: 'var(--line)', background: 'var(--panel)' }}
            >
              +
            </button>
            <button
              type="button"
              onClick={fitConnection}
              className="min-h-9 rounded border px-3 text-dense"
              style={{ borderColor: 'var(--line)', background: 'var(--panel)' }}
            >
              Fit connection
            </button>
            <button
              type="button"
              disabled
              className="min-h-9 rounded border px-3 text-dense opacity-50"
              style={{ borderColor: 'var(--line)', background: 'var(--panel)' }}
              title="Replay arrives in T13 (P1)"
            >
              {'▶'} Replay · P1
            </button>
            <MockBadge />
          </div>
        </div>

        <Overview wellId={wellId} fullRange={fullRange} sync={sync} onRangeSettled={handleRangeSettled} />

        <div className="relative rounded border" style={{ borderColor: 'var(--line)', background: 'var(--panel)' }}>
          <DepthTime wellId={wellId} fullRange={fullRange} sync={sync} onRangeSettled={handleRangeSettled} />
          <RibbonTrack
            intervals={rigState.data ?? []}
            fullRange={fullRange}
            sync={sync}
            onRangeSettled={handleRangeSettled}
          />
          <DdrLaneTrack
            rows={ddr.data ?? []}
            mismatches={mismatches.data ?? []}
            fullRange={fullRange}
            sync={sync}
            onRangeSettled={handleRangeSettled}
            onMismatchClick={setOpenMismatchId}
          />
          <TrackStack
            wellId={wellId}
            tracks={TRACKS}
            units={TRACK_UNITS}
            timeRange={effectiveRange}
            fullRange={fullRange}
            sync={sync}
            onRangeSettled={handleRangeSettled}
            plotWidthPx={900}
          />

          {openMismatch && (
            <div className="absolute left-1/2 top-60 z-10 -translate-x-1/2">
              <MismatchPopover
                mismatch={openMismatch}
                narrative={openDdrRow?.narrative ?? ''}
                reportDate={openDdrRow?.report_date ?? ''}
                onClose={() => setOpenMismatchId(null)}
                onZoomToWindow={() => {
                  const padded = clampRange(
                    openMismatch.t0 - 5 * 60_000,
                    openMismatch.t1 + 5 * 60_000,
                    fullRange[0],
                    fullRange[1],
                  )
                  sync.setRange(padded)
                  handleRangeSettled(padded)
                  setOpenMismatchId(null)
                }}
                onAskCopilot={() => {
                  setOpenMismatchId(null)
                  setTimeRange([openMismatch.t0, openMismatch.t1])
                  setCopilotPrefill(
                    `Why does the sensor data say ${RIG_STATE_LABEL[openMismatch.sensor_state]} ` +
                      `here while the daily report codes it ${openMismatch.ddr_code}?`,
                  )
                  setPanel('copilot')
                }}
              />
            </div>
          )}
        </div>

        <RigStateLegend />
      </main>
    </div>
  )
}
