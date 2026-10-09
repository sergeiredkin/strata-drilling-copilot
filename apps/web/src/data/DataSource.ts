// The DataSource interface — docs/03_ARCHITECTURE.md §3.1. StaticSource reads
// apps/web/public/data (fresh clone, no backend); HttpSource reads a live API. Both
// return identical shapes, enforced by the generated zod schemas.
import type {
  ChannelId,
  CopilotAnswer,
  CopilotContext,
  CopilotEvent,
  DdrActivity,
  DepthTimeBlock,
  EvalReport,
  Evidence,
  EvidenceId,
  FormationPrediction,
  FormationReport,
  IltReport,
  Issue,
  KpiReport,
  Mismatch,
  ModelCard,
  Precursors,
  Reconciliation,
  ReplayEvent,
  ReproManifest,
  RigStateInterval,
  Section,
  SeriesIndex,
  SessionIndex,
  WellId,
  WellList,
} from '../contracts/types'
import type { SeriesChunk } from './seriesDecoder'

export type IssueQuery = {
  well?: WellId
  type?: string
  formation?: string
}

export type DataSource = {
  wells(): Promise<WellList>
  sections(id: WellId): Promise<Section[]>
  depthTime(id: WellId): Promise<DepthTimeBlock>
  seriesIndex(id: WellId): Promise<SeriesIndex>
  seriesChunk(id: WellId, ch: ChannelId, level: number, chunk: number): Promise<SeriesChunk>
  rigState(id: WellId, t0: number, t1: number): Promise<RigStateInterval[]>
  ddr(id: WellId, t0: number, t1: number): Promise<DdrActivity[]>
  mismatches(id: WellId): Promise<Mismatch[]>
  kpis(id: WellId): Promise<KpiReport>
  ilt(id: WellId): Promise<IltReport>
  reconciliation(id?: WellId): Promise<Reconciliation>
  formations(id: WellId): Promise<FormationReport>
  formationPred(id: WellId): Promise<FormationPrediction>
  modelCard(model: 'formation' | 'events'): Promise<ModelCard>
  issues(q: IssueQuery): Promise<Issue[]>
  precursors(issueId: string): Promise<Precursors>
  evidence(id: EvidenceId): Promise<Evidence>
  sessions(): Promise<SessionIndex>
  ask(question: string, ctx: CopilotContext, sessionId?: string): AsyncIterable<CopilotEvent>
  replay(id: WellId, speed: 1 | 10 | 60, fromT: number): AsyncIterable<ReplayEvent>
  evalReport(): Promise<EvalReport>
  repro(): Promise<ReproManifest>
}

/** Thrown by both sources for a missing/unreadable fixture or a failed live request, and for
 * a zod validation failure in dev/test — always names the path so the error is actionable. */
export class StrataDataError extends Error {
  readonly path: string

  constructor(message: string, path: string) {
    super(message)
    this.name = 'StrataDataError'
    this.path = path
  }
}

export type CopilotAnswerKind = CopilotAnswer['kind']
