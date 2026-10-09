// "How lost time is defined" panel, comp S3-Performance.dc.html. Text comes straight from
// ilt.definition — nothing here is hardcoded per-well copy.
import type { IltReport } from '../../contracts/types'

export function IltDefinition({ definition }: { definition: IltReport['definition'] }) {
  return (
    <div className="flex flex-col gap-1.5">
      <ol className="m-0 flex flex-col gap-1.5 pl-[18px] text-dense leading-snug text-text">
        <li>Each connection, stand and flat-time block is timed from rig-state intervals.</li>
        <li>
          Composite best = P{definition.percentile} per KPI, per hole section, per well
          (baseline: {definition.baseline.replace('_', ' ')}).
        </li>
        <li>{definition.text}</li>
        <li>Intervals overlapping a data gap are excluded, and counted on the Trust page.</li>
      </ol>
    </div>
  )
}
