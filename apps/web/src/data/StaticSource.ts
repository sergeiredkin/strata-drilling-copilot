// Reads apps/web/public/data — the export `04_DATA_CONTRACTS.md` §3 lays out. This is what
// runs from a fresh clone with no backend and no API key (docs/01_PRODUCT_SPEC.md §4).
import type {
  ChannelId,
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
import {
  ddrActivitySchema,
  evalReportSchema,
  iltReportSchema,
  issueSchema,
  kpiReportSchema,
  mismatchSchema,
  reconciliationSchema,
  reproManifestSchema,
  rigStateIntervalSchema,
  sectionSchema,
  seriesIndexSchema,
  sessionIndexSchema,
  wellListSchema,
} from '../contracts/zod'
import type { DataSource, IssueQuery } from './DataSource'
import { StrataDataError } from './DataSource'
import { EvidenceIndex } from './evidenceIndex'
import { decodeStrsBlock, type SeriesChunk } from './seriesDecoder'
import { isFastMode, playSession } from './sessionPlayer'
import { z } from 'zod'

const shouldValidate = (): boolean => Boolean(import.meta.env.DEV)

export class StaticSource implements DataSource {
  private readonly base: string
  private readonly evidenceIdx: EvidenceIndex
  private seriesIndexCache = new Map<WellId, Promise<SeriesIndex>>()

  constructor(base = '/data') {
    this.base = base.endsWith('/') ? base.slice(0, -1) : base
    this.evidenceIdx = new EvidenceIndex((path) => this.fetchJson(path))
  }

  private async fetchJson<T>(path: string, schema?: z.ZodType<T>): Promise<T> {
    const url = `${this.base}/${path}`
    let res: Response
    try {
      res = await fetch(url)
    } catch {
      throw new StrataDataError(`${path}: network error fetching ${url}`, path)
    }
    if (!res.ok) {
      throw new StrataDataError(`${path}: HTTP ${res.status} fetching ${url}`, path)
    }
    const data: unknown = await res.json()
    if (schema && shouldValidate()) {
      const result = schema.safeParse(data)
      if (!result.success) {
        const issues = result.error.issues.map((i) => `${i.path.join('.') || '<root>'}: ${i.message}`)
        throw new StrataDataError(`${path}: schema validation failed — ${issues.join('; ')}`, path)
      }
      return result.data
    }
    return data as T
  }

  private async fetchBinary(path: string): Promise<ArrayBuffer> {
    const url = `${this.base}/${path}`
    let res: Response
    try {
      res = await fetch(url)
    } catch {
      throw new StrataDataError(`${path}: network error fetching ${url}`, path)
    }
    if (!res.ok) {
      throw new StrataDataError(`${path}: HTTP ${res.status} fetching ${url}`, path)
    }
    return res.arrayBuffer()
  }

  async wells(): Promise<WellList> {
    return this.fetchJson('wells.json', wellListSchema as unknown as z.ZodType<WellList>)
  }

  async sections(id: WellId): Promise<Section[]> {
    return this.fetchJson(`wells/${id}/sections.json`, z.array(sectionSchema) as unknown as z.ZodType<Section[]>)
  }

  async depthTime(id: WellId): Promise<DepthTimeBlock> {
    return this.fetchJson(`wells/${id}/depthtime.json`)
  }

  async seriesIndex(id: WellId): Promise<SeriesIndex> {
    let cached = this.seriesIndexCache.get(id)
    if (!cached) {
      cached = this.fetchJson(`wells/${id}/series/index.json`, seriesIndexSchema as unknown as z.ZodType<SeriesIndex>)
      this.seriesIndexCache.set(id, cached)
    }
    return cached
  }

  async seriesChunk(id: WellId, ch: ChannelId, level: number, chunk: number): Promise<SeriesChunk> {
    const index = await this.seriesIndex(id)
    const channel = index.channels[ch]
    if (!channel) {
      throw new StrataDataError(`well ${id} has no channel ${ch}`, `wells/${id}/series/index.json`)
    }
    const levelMeta = channel.levels.find((l) => l.level === level)
    const chunkMeta = levelMeta?.chunks.find((c) => c.i === chunk)
    if (!chunkMeta) {
      throw new StrataDataError(
        `well ${id} channel ${ch} has no level ${level} chunk ${chunk}`,
        `wells/${id}/series/index.json`,
      )
    }
    const buf = await this.fetchBinary(`wells/${id}/${chunkMeta.file}`)
    return decodeStrsBlock(buf)
  }

  async rigState(id: WellId, t0: number, t1: number): Promise<RigStateInterval[]> {
    const all = await this.fetchJson(
      `wells/${id}/rigstate.json`,
      z.array(rigStateIntervalSchema) as unknown as z.ZodType<RigStateInterval[]>,
    )
    return all.filter((s) => s.t1 > t0 && s.t0 < t1)
  }

  async ddr(id: WellId, t0: number, t1: number): Promise<DdrActivity[]> {
    const all = await this.fetchJson(`wells/${id}/ddr.json`, z.array(ddrActivitySchema) as unknown as z.ZodType<DdrActivity[]>)
    return all.filter((r) => r.t1 > t0 && r.t0 < t1)
  }

  async mismatches(id: WellId): Promise<Mismatch[]> {
    return this.fetchJson(`wells/${id}/mismatches.json`, z.array(mismatchSchema) as unknown as z.ZodType<Mismatch[]>)
  }

  async kpis(id: WellId): Promise<KpiReport> {
    return this.fetchJson(`wells/${id}/kpis.json`, kpiReportSchema as unknown as z.ZodType<KpiReport>)
  }

  async ilt(id: WellId): Promise<IltReport> {
    return this.fetchJson(`wells/${id}/ilt.json`, iltReportSchema as unknown as z.ZodType<IltReport>)
  }

  async reconciliation(id?: WellId): Promise<Reconciliation> {
    const path = id ? `reconciliation/${id}.json` : 'reconciliation/all.json'
    return this.fetchJson(path, reconciliationSchema as unknown as z.ZodType<Reconciliation>)
  }

  async formations(id: WellId): Promise<FormationReport> {
    return this.fetchJson(`wells/${id}/formations.json`)
  }

  async formationPred(id: WellId): Promise<FormationPrediction> {
    return this.fetchJson(`wells/${id}/formation_pred.json`)
  }

  async modelCard(model: 'formation' | 'events'): Promise<ModelCard> {
    return this.fetchJson(`models/${model}_card.json`)
  }

  async issues(q: IssueQuery): Promise<Issue[]> {
    const all = await this.fetchJson('issues.json', z.array(issueSchema) as unknown as z.ZodType<Issue[]>)
    return all.filter(
      (i) =>
        (!q.well || i.well === q.well) &&
        (!q.type || i.type === q.type) &&
        (!q.formation || i.formation === q.formation),
    )
  }

  async precursors(issueId: string): Promise<Precursors> {
    return this.fetchJson(`issues/${issueId}_precursors.json`)
  }

  async evidence(id: EvidenceId): Promise<Evidence> {
    return this.evidenceIdx.get(id)
  }

  async sessions(): Promise<SessionIndex> {
    return this.fetchJson('copilot/sessions/index.json', sessionIndexSchema as unknown as z.ZodType<SessionIndex>)
  }

  ask(question: string, _ctx: CopilotContext, sessionId?: string): AsyncIterable<CopilotEvent> {
    return this.askImpl(question, sessionId)
  }

  private async *askImpl(question: string, sessionId?: string): AsyncGenerator<CopilotEvent, void, unknown> {
    const index = await this.sessions()
    const match = sessionId
      ? index.sessions.find((s) => s.id === sessionId)
      : index.sessions.find((s) => s.question.trim().toLowerCase() === question.trim().toLowerCase())

    if (!match) {
      const event: CopilotEvent = {
        type: 'answer',
        dt_ms: 0,
        answer: {
          kind: 'live_mode_required',
          answer: 'This question has no recorded static-mode session. Connect a live API (VITE_API_URL) to ask freely.',
          claims: [],
          ddr_quotes: [],
          reasoning: '',
          assumptions: [],
          confidence: 'low',
          confidence_reason: 'no recorded session matches this question in static mode.',
          trace: [],
        },
      }
      yield event
      return
    }

    const lines = (await this.fetchText(match.file)).split('\n').filter((l) => l.trim().length > 0)
    const events = lines.map((l) => JSON.parse(l) as CopilotEvent)
    yield* playSession(events, { fast: isFastMode() })
  }

  private async fetchText(path: string): Promise<string> {
    const url = `${this.base}/${path}`
    const res = await fetch(url)
    if (!res.ok) {
      throw new StrataDataError(`${path}: HTTP ${res.status} fetching ${url}`, path)
    }
    return res.text()
  }

  // eslint-disable-next-line require-yield
  async *replay(_id: WellId, _speed: 1 | 10 | 60, _fromT: number): AsyncIterable<ReplayEvent> {
    // P1 (T13.2) — static replay streams L0 chunks + replay_events.json with a timer.
    return
  }

  async evalReport(): Promise<EvalReport> {
    return this.fetchJson('eval.json', evalReportSchema as unknown as z.ZodType<EvalReport>)
  }

  async repro(): Promise<ReproManifest> {
    return this.fetchJson('repro.json', reproManifestSchema as unknown as z.ZodType<ReproManifest>)
  }
}
