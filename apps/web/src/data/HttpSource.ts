// Live mode — hits the FastAPI service (T8.3) at `contracts/endpoints.yaml` paths. Until that
// service exists, every call below will simply fail at the network layer; that's expected: the
// product works in static mode without it (docs/01_PRODUCT_SPEC.md §4).
import type {
  ChannelId,
  CopilotContext,
  CopilotEvent,
  DdrActivity,
  DepthSeries,
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
import type { DataSource, IssueQuery } from './DataSource'
import { StrataDataError } from './DataSource'
import { decodeStrsBlock, type SeriesChunk } from './seriesDecoder'
import { bridgeWebSocket, replayWsUrl } from './wsReplay'

export class HttpSource implements DataSource {
  constructor(private readonly baseUrl: string) {}

  private async getJson<T>(path: string): Promise<T> {
    const url = `${this.baseUrl}${path}`
    let res: Response
    try {
      res = await fetch(url)
    } catch {
      throw new StrataDataError(`${path}: network error fetching ${url}`, path)
    }
    if (!res.ok) {
      throw new StrataDataError(`${path}: HTTP ${res.status} fetching ${url}`, path)
    }
    return (await res.json()) as T
  }

  async wells(): Promise<WellList> {
    return this.getJson('/wells')
  }

  async sections(id: WellId): Promise<Section[]> {
    return this.getJson(`/wells/${id}/sections`)
  }

  async depthTime(id: WellId): Promise<DepthTimeBlock> {
    return this.getJson(`/wells/${id}/depthtime`)
  }

  async seriesIndex(id: WellId): Promise<SeriesIndex> {
    return this.getJson(`/wells/${id}/series`)
  }

  async seriesChunk(id: WellId, ch: ChannelId, level: number, _chunk: number): Promise<SeriesChunk> {
    const url = `${this.baseUrl}/wells/${id}/channels?ch=${ch}&level=${level}`
    const res = await fetch(url)
    if (!res.ok) {
      throw new StrataDataError(`channels: HTTP ${res.status} fetching ${url}`, 'channels')
    }
    return decodeStrsBlock(await res.arrayBuffer())
  }

  async rigState(id: WellId, t0: number, t1: number): Promise<RigStateInterval[]> {
    return this.getJson(`/wells/${id}/rigstate?start=${t0}&end=${t1}`)
  }

  async ddr(id: WellId, t0: number, t1: number): Promise<DdrActivity[]> {
    return this.getJson(`/wells/${id}/ddr?start=${t0}&end=${t1}`)
  }

  async mismatches(id: WellId): Promise<Mismatch[]> {
    return this.getJson(`/wells/${id}/mismatches`)
  }

  async kpis(id: WellId): Promise<KpiReport> {
    return this.getJson(`/wells/${id}/kpis`)
  }

  async ilt(id: WellId): Promise<IltReport> {
    return this.getJson(`/wells/${id}/ilt`)
  }

  async reconciliation(id?: WellId): Promise<Reconciliation> {
    return this.getJson(id ? `/reconciliation?well=${id}` : '/reconciliation')
  }

  async formations(id: WellId): Promise<FormationReport> {
    return this.getJson(`/wells/${id}/formations`)
  }

  async formationPred(id: WellId): Promise<FormationPrediction> {
    return this.getJson(`/wells/${id}/formation-pred`)
  }

  async depthSeries(id: WellId): Promise<DepthSeries> {
    return this.getJson(`/wells/${id}/depth-series`)
  }

  async modelCard(model: 'formation' | 'events'): Promise<ModelCard> {
    return this.getJson(`/models/${model}/card`)
  }

  async issues(q: IssueQuery): Promise<Issue[]> {
    const params = new URLSearchParams()
    if (q.well) params.set('well', q.well)
    if (q.type) params.set('type', q.type)
    if (q.formation) params.set('formation', q.formation)
    const qs = params.toString()
    return this.getJson(`/issues${qs ? `?${qs}` : ''}`)
  }

  async precursors(issueId: string): Promise<Precursors> {
    return this.getJson(`/issues/${issueId}/precursors`)
  }

  async evidence(id: EvidenceId): Promise<Evidence> {
    return this.getJson(`/evidence/${id}`)
  }

  async sessions(): Promise<SessionIndex> {
    return this.getJson('/copilot/sessions')
  }

  async *ask(question: string, ctx: CopilotContext, sessionId?: string): AsyncIterable<CopilotEvent> {
    const res = await fetch(`${this.baseUrl}/copilot/ask`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ question, context: ctx, session_id: sessionId }),
    })
    if (!res.ok || !res.body) {
      throw new StrataDataError(`copilot/ask: HTTP ${res.status}`, 'copilot/ask')
    }
    const reader = res.body.getReader()
    const decoder = new TextDecoder()
    let buffer = ''
    for (;;) {
      const { done, value } = await reader.read()
      if (done) break
      buffer += decoder.decode(value, { stream: true })
      const parts = buffer.split('\n\n')
      buffer = parts.pop() ?? ''
      for (const part of parts) {
        const dataLine = part.split('\n').find((l) => l.startsWith('data:'))
        if (dataLine) yield JSON.parse(dataLine.slice(5).trim()) as CopilotEvent
      }
    }
  }

  async *replay(id: WellId, speed: 1 | 10 | 60, fromT: number): AsyncIterable<ReplayEvent> {
    const socket = new WebSocket(replayWsUrl(this.baseUrl, id, speed, fromT))
    yield* bridgeWebSocket(socket)
  }

  async evalReport(): Promise<EvalReport> {
    return this.getJson('/eval')
  }

  async repro(): Promise<ReproManifest> {
    return this.getJson('/meta/repro')
  }
}
