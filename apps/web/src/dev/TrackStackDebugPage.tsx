// Temporary dev-only harness for visually checking TrackStack while S2 is being built.
// Not part of T6.x's file list — deleted once T6.5 assembles the real S2 screen.
import { useMemo, useState } from 'react'
import { DdrLaneTrack } from '../charts/TrackStack/DdrLaneTrack'
import { RibbonTrack } from '../charts/TrackStack/RibbonTrack'
import { RigStateLegend } from '../charts/TrackStack/RigStateLegend'
import { DepthTime } from '../charts/DepthTime/DepthTime'
import { Overview } from '../charts/DepthTime/Overview'
import { createTimeRangeSync } from '../charts/TrackStack/sync'
import { TrackStack, type TrackDef } from '../charts/TrackStack/TrackStack'
import { useDdr, useMismatches, useRigState } from '../data/hooks'
import { MismatchPopover } from '../screens/S2Workspace/MismatchPopover'

const WELL_ID = '15_9-F-11_A'
const FULL_RANGE: [number, number] = [1_700_000_000_000, 1_700_000_000_000 + 4 * 86_400_000]

const TRACKS: TrackDef[] = [
  { channel: 'HKLD', name: 'Hookload' },
  { channel: 'WOB', name: 'WOB' },
  { channel: 'RPM', name: 'RPM' },
  { channel: 'TORQ', name: 'Torque' },
  { channel: 'SPP', name: 'SPP' },
  { channel: 'FLOWIN', name: 'Flow in' },
]

const UNITS = { HKLD: 'kN', WOB: 'kN', RPM: 'rpm', TORQ: 'kN.m', SPP: 'bar', FLOWIN: 'L/min' }

export function TrackStackDebugPage() {
  const sync = useMemo(() => createTimeRangeSync(FULL_RANGE), [])
  const [range, setRange] = useState<[number, number]>(FULL_RANGE)
  const [openMismatchId, setOpenMismatchId] = useState<string | null>(null)

  const rigState = useRigState(WELL_ID, FULL_RANGE[0], FULL_RANGE[1])
  const ddr = useDdr(WELL_ID, FULL_RANGE[0], FULL_RANGE[1])
  const mismatches = useMismatches(WELL_ID)
  const openMismatch = mismatches.data?.find((m) => m.id === openMismatchId) ?? null
  const openDdrRow = openMismatch ? ddr.data?.find((r) => r.id === openMismatch.ddr_activity_id) : undefined

  return (
    <div className="min-h-screen bg-bg p-6 text-text" data-theme="dark">
      <h1 className="mb-2 text-page-title">TrackStack debug</h1>
      <p className="mb-4 text-dense text-text-2">
        Range: {range[0]} → {range[1]} ({((range[1] - range[0]) / 60000).toFixed(1)} min). Wheel to zoom,
        drag to pan.
      </p>
      <div className="mb-4">
        <Overview wellId={WELL_ID} fullRange={FULL_RANGE} sync={sync} onRangeSettled={setRange} />
      </div>
      <div className="relative rounded border" style={{ borderColor: 'var(--line)', background: 'var(--panel)' }}>
        <DepthTime wellId={WELL_ID} fullRange={FULL_RANGE} sync={sync} onRangeSettled={setRange} />
        <RibbonTrack
          intervals={rigState.data ?? []}
          fullRange={FULL_RANGE}
          sync={sync}
          onRangeSettled={setRange}
        />
        <DdrLaneTrack
          rows={ddr.data ?? []}
          mismatches={mismatches.data ?? []}
          fullRange={FULL_RANGE}
          sync={sync}
          onRangeSettled={setRange}
          onMismatchClick={setOpenMismatchId}
        />
        <TrackStack
          wellId={WELL_ID}
          tracks={TRACKS}
          units={UNITS}
          timeRange={range}
          fullRange={FULL_RANGE}
          sync={sync}
          onRangeSettled={setRange}
          plotWidthPx={900}
        />
        {openMismatch && (
          <div className="absolute left-1/2 top-24 z-10 -translate-x-1/2">
            <MismatchPopover
              mismatch={openMismatch}
              narrative={openDdrRow?.narrative ?? ''}
              reportDate={openDdrRow?.report_date ?? ''}
              onClose={() => setOpenMismatchId(null)}
              onZoomToWindow={() => {
                sync.setRange([openMismatch.t0 - 5 * 60_000, openMismatch.t1 + 5 * 60_000])
                setRange([openMismatch.t0 - 5 * 60_000, openMismatch.t1 + 5 * 60_000])
              }}
              onAskCopilot={() => {
                /* T8.2 wires real copilot context */
              }}
            />
          </div>
        )}
      </div>
      <div className="mt-3">
        <RigStateLegend />
      </div>
    </div>
  )
}
