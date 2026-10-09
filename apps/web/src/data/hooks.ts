// TanStack Query hooks over the DataSource (docs/02_IMPLEMENTATION_PLAN.md T4.1). Each chunk is
// cached by (well, channel, level, chunk index) so pan/zoom in S2 reuses what it already fetched.
import { useQueries, useQuery, type UseQueryResult } from '@tanstack/react-query'
import type { ChannelId, WellId } from '../contracts/types'
import type { DataSource, IssueQuery } from './DataSource'
import { getDataSource } from './createDataSource'
import { chooseLevel, type DecodedSeries } from './seriesDecoder'
import { toNullableArrays } from './seriesDecoder'

function useDataSource(): DataSource {
  return getDataSource()
}

export function useWells() {
  const ds = useDataSource()
  return useQuery({ queryKey: ['wells'], queryFn: () => ds.wells() })
}

export function useSections(wellId: WellId | undefined) {
  const ds = useDataSource()
  return useQuery({
    queryKey: ['sections', wellId],
    queryFn: () => ds.sections(wellId as WellId),
    enabled: Boolean(wellId),
  })
}

export function useDepthTime(wellId: WellId | undefined) {
  const ds = useDataSource()
  return useQuery({
    queryKey: ['depthTime', wellId],
    queryFn: () => ds.depthTime(wellId as WellId),
    enabled: Boolean(wellId),
  })
}

export function useSeriesIndex(wellId: WellId | undefined) {
  const ds = useDataSource()
  return useQuery({
    queryKey: ['seriesIndex', wellId],
    queryFn: () => ds.seriesIndex(wellId as WellId),
    enabled: Boolean(wellId),
  })
}

export function useRigState(wellId: WellId | undefined, t0: number, t1: number) {
  const ds = useDataSource()
  return useQuery({
    queryKey: ['rigState', wellId, t0, t1],
    queryFn: () => ds.rigState(wellId as WellId, t0, t1),
    enabled: Boolean(wellId),
  })
}

export function useDdr(wellId: WellId | undefined, t0: number, t1: number) {
  const ds = useDataSource()
  return useQuery({
    queryKey: ['ddr', wellId, t0, t1],
    queryFn: () => ds.ddr(wellId as WellId, t0, t1),
    enabled: Boolean(wellId),
  })
}

export function useMismatches(wellId: WellId | undefined) {
  const ds = useDataSource()
  return useQuery({
    queryKey: ['mismatches', wellId],
    queryFn: () => ds.mismatches(wellId as WellId),
    enabled: Boolean(wellId),
  })
}

export function useKpis(wellId: WellId | undefined) {
  const ds = useDataSource()
  return useQuery({
    queryKey: ['kpis', wellId],
    queryFn: () => ds.kpis(wellId as WellId),
    enabled: Boolean(wellId),
  })
}

export function useIlt(wellId: WellId | undefined) {
  const ds = useDataSource()
  return useQuery({
    queryKey: ['ilt', wellId],
    queryFn: () => ds.ilt(wellId as WellId),
    enabled: Boolean(wellId),
  })
}

export function useReconciliation(wellId?: WellId) {
  const ds = useDataSource()
  return useQuery({
    queryKey: ['reconciliation', wellId ?? 'all'],
    queryFn: () => ds.reconciliation(wellId),
  })
}

export function useIssues(query: IssueQuery) {
  const ds = useDataSource()
  return useQuery({ queryKey: ['issues', query], queryFn: () => ds.issues(query) })
}

export function useEvidence(evidenceId: string | undefined) {
  const ds = useDataSource()
  return useQuery({
    queryKey: ['evidence', evidenceId],
    queryFn: () => ds.evidence(evidenceId as string),
    enabled: Boolean(evidenceId),
  })
}

export function useSessions() {
  const ds = useDataSource()
  return useQuery({ queryKey: ['sessions'], queryFn: () => ds.sessions() })
}

export function useEvalReport() {
  const ds = useDataSource()
  return useQuery({ queryKey: ['evalReport'], queryFn: () => ds.evalReport() })
}

export function useRepro() {
  const ds = useDataSource()
  return useQuery({ queryKey: ['repro'], queryFn: () => ds.repro() })
}

export function useModelCard(model: 'formation' | 'events') {
  const ds = useDataSource()
  return useQuery({ queryKey: ['modelCard', model], queryFn: () => ds.modelCard(model), retry: false })
}

/** Picks the right LOD level for [t0, t1) at `plotWidthPx`, fetches every chunk of every
 * requested channel that overlaps the window, and concatenates + decodes them (NaN -> null). */
export function useSeriesWindow(
  wellId: WellId | undefined,
  channels: ChannelId[],
  t0: number,
  t1: number,
  plotWidthPx: number,
): Record<ChannelId, UseQueryResult<DecodedSeries>> {
  const ds = useDataSource()
  const level = chooseLevel(t0, t1, plotWidthPx)
  const index = useSeriesIndex(wellId)

  const perChannel = useQueries({
    queries: channels.map((ch) => {
      const levelMeta = index.data?.channels[ch]?.levels.find((l) => l.level === level)
      const chunkIds = (levelMeta?.chunks ?? [])
        .filter((c) => c.t1 > t0 && c.t0 < t1)
        .map((c) => c.i)

      return {
        queryKey: ['seriesWindow', wellId, ch, level, chunkIds],
        queryFn: async () => {
          const chunks = await Promise.all(
            chunkIds.map((i) => ds.seriesChunk(wellId as WellId, ch, level, i)),
          )
          const decoded = chunks.map(toNullableArrays)
          const t = decoded.flatMap((d) => Array.from(d.t))
          const min = decoded.flatMap((d) => d.min)
          const max = decoded.flatMap((d) => d.max)
          return { t: Float64Array.from(t), min, max } satisfies DecodedSeries
        },
        enabled: Boolean(wellId) && Boolean(index.data) && chunkIds.length > 0,
      }
    }),
  })

  const result: Partial<Record<ChannelId, UseQueryResult<DecodedSeries>>> = {}
  channels.forEach((ch, i) => {
    result[ch] = perChannel[i] as UseQueryResult<DecodedSeries>
  })
  return result as Record<ChannelId, UseQueryResult<DecodedSeries>>
}
