// Evidence shard lookup — docs/04_DATA_CONTRACTS.md §3: evidence/shards.json maps an id to its
// shard file (evidence/{00..ff}.json), avoiding one JSON file per evidence record.
import type { Evidence, EvidenceId } from '../contracts/types'
import { StrataDataError } from './DataSource'

export type FetchJson = (path: string) => Promise<unknown>

export class EvidenceIndex {
  private shardOf: Record<string, string> | null = null
  private shardCache = new Map<string, Record<string, Evidence>>()

  constructor(private readonly fetchJson: FetchJson) {}

  async get(id: EvidenceId): Promise<Evidence> {
    if (!this.shardOf) {
      this.shardOf = (await this.fetchJson('evidence/shards.json')) as Record<string, string>
    }
    const shard = this.shardOf[id]
    if (!shard) {
      throw new StrataDataError(`no evidence record for ${id}`, 'evidence/shards.json')
    }

    let records = this.shardCache.get(shard)
    if (!records) {
      records = (await this.fetchJson(`evidence/${shard}.json`)) as Record<string, Evidence>
      this.shardCache.set(shard, records)
    }

    const record = records[id]
    if (!record) {
      throw new StrataDataError(`evidence shard ${shard} has no record for ${id}`, `evidence/${shard}.json`)
    }
    return record
  }
}
