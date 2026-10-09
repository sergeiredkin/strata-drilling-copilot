// Temporary dev-only harness for visually checking TrackStack while S2 is being built.
// Not part of T6.x's file list — deleted once T6.5 assembles the real S2 screen.
import { useMemo, useState } from 'react'
import { createTimeRangeSync } from '../charts/TrackStack/sync'
import { TrackStack, type TrackDef } from '../charts/TrackStack/TrackStack'

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

  return (
    <div className="min-h-screen bg-bg p-6 text-text" data-theme="dark">
      <h1 className="mb-2 text-page-title">TrackStack debug</h1>
      <p className="mb-4 text-dense text-text-2">
        Range: {range[0]} → {range[1]} ({((range[1] - range[0]) / 60000).toFixed(1)} min). Wheel to zoom,
        drag to pan.
      </p>
      <div className="rounded border" style={{ borderColor: 'var(--line)', background: 'var(--panel)' }}>
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
      </div>
    </div>
  )
}
