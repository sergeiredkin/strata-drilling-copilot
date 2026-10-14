// T11.5 depth<->time linking — docs/06_SCREENS.md S6 acceptance: "clicking an interval opens S2
// at the corresponding time intervals." `depthtime.json` (`DepthTimeBlock`) is the only bridge
// between the two indices: a BITDEPTH sample per timestamp, strided (every 60s in the real
// export — `export/real_well.py:build_depthtime_json`), so this is minute-resolution, not
// pixel-exact, but that's the actual resolution of the only data that links them.
import type { DepthTimeBlock } from '../../contracts/types'

export type TimeWindow = { t0: number; t1: number }

/** The [min, max] timestamp among samples whose BITDEPTH falls in `[mdTop, mdBase)`. `null` when
 * no sample in `depthTime` ever had the bit in that range — an honest "no link available", not
 * a guessed window. */
export function mdIntervalToTimeWindow(
  depthTime: DepthTimeBlock,
  mdTop: number,
  mdBase: number,
): TimeWindow | null {
  let t0: number | null = null
  let t1: number | null = null
  for (let i = 0; i < depthTime.t.length; i++) {
    const md = depthTime.bit_md[i]
    if (md === null || md === undefined || md < mdTop || md >= mdBase) continue
    const t = depthTime.t[i]
    if (t === undefined) continue
    if (t0 === null || t < t0) t0 = t
    if (t1 === null || t > t1) t1 = t
  }
  return t0 !== null && t1 !== null ? { t0, t1 } : null
}
