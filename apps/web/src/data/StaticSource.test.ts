import { beforeAll, describe, expect, it } from 'vitest'
import { installFixtureFetch } from '../test/fixtureFetch'
import { StrataDataError } from './DataSource'
import { StaticSource } from './StaticSource'

beforeAll(() => {
  installFixtureFetch()
  window.history.replaceState({}, '', '/?fast=1') // skip sessionPlayer's recorded delays in tests
})

const RICH_WELL = '15_9-F-11_A'
const SPARSE_WELL = '15_9-F-5'

describe('StaticSource against the real fixtures', () => {
  const ds = new StaticSource('/data')

  it('wells() returns all 9 wells, exactly one real (T10.4)', async () => {
    const list = await ds.wells()
    expect(list.wells).toHaveLength(9)
    expect(list.wells.filter((w) => !w.is_mock).map((w) => w.id)).toEqual([RICH_WELL])
  })

  it('sections() returns the dense-window section for a detailed well', async () => {
    // Not RICH_WELL: real wells' sections.json is honestly empty (sections.parquet derivation
    // isn't built yet, docs/DATA_INVENTORY.md) -- this exercises a mock well that still has one.
    const sections = await ds.sections(SPARSE_WELL)
    expect(sections.length).toBeGreaterThan(0)
    expect(sections[0]?.md_base).toBeGreaterThan(sections[0]?.md_top ?? 0)
  })

  it('depthTime() returns parallel t/bit_md/hole_md arrays', async () => {
    const dt = await ds.depthTime(RICH_WELL)
    expect(dt.t.length).toBe(dt.bit_md.length)
    expect(dt.t.length).toBe(dt.hole_md.length)
    expect(dt.t.length).toBeGreaterThan(0)
  })

  it('seriesIndex() + seriesChunk() round-trip a real L0 chunk', async () => {
    const index = await ds.seriesIndex(RICH_WELL)
    const hkld = index.channels.HKLD
    expect(hkld).toBeDefined()
    const l0 = hkld?.levels.find((l) => l.level === 0)
    expect(l0?.chunks.length).toBeGreaterThan(0)

    const chunk = await ds.seriesChunk(RICH_WELL, 'HKLD', 0, 0)
    expect(chunk.n).toBeGreaterThan(0)
    expect(chunk.bucketS).toBe(1)
  })

  it('rigState() filters to the requested window', async () => {
    const all = await ds.rigState(RICH_WELL, 0, Number.MAX_SAFE_INTEGER)
    const first = all[0]
    if (!first) throw new Error('expected at least one rig-state interval in the fixture')
    const windowed = await ds.rigState(RICH_WELL, first.t0, first.t0 + 1)
    expect(windowed.length).toBeGreaterThan(0)
    expect(windowed.every((s) => s.t1 > first.t0)).toBe(true)
  })

  it('ddr() filters to the requested window', async () => {
    const all = await ds.ddr(RICH_WELL, 0, Number.MAX_SAFE_INTEGER)
    expect(all.length).toBeGreaterThan(0)
  })

  it('mismatches() returns the rich well mismatch list', async () => {
    const mm = await ds.mismatches(RICH_WELL)
    expect(mm.length).toBeGreaterThan(0)
  })

  it('kpis() and ilt() validate and are internally consistent', async () => {
    const kpis = await ds.kpis(RICH_WELL)
    expect(kpis.well).toBe(RICH_WELL)
    const ilt = await ds.ilt(RICH_WELL)
    const catSum = ilt.by_category.reduce((s, c) => s + (c.hours.value ?? 0), 0)
    expect(ilt.total.value).toBeCloseTo(catSum, 6)
  })

  it('reconciliation() works both per-well and for "all"', async () => {
    const perWell = await ds.reconciliation(RICH_WELL)
    expect(perWell.scope).toBe(RICH_WELL)
    const all = await ds.reconciliation()
    expect(all.scope).toBe('all')
  })

  it('evidence() resolves a real id via the shard map', async () => {
    const kpis = await ds.kpis(RICH_WELL)
    const card = kpis.cards.find((c) => c.value.evidence_id)
    if (!card) throw new Error('expected at least one kpi card with an evidence id')
    const ev = await ds.evidence(card.value.evidence_id)
    expect(ev.id).toBe(card.value.evidence_id)
  })

  it('evidence() throws a readable StrataDataError for an unknown id', async () => {
    await expect(ds.evidence('ev_0000000000')).rejects.toThrow(StrataDataError)
  })

  it('sessions() lists the 3 recorded sessions', async () => {
    const idx = await ds.sessions()
    expect(idx.sessions).toHaveLength(3)
  })

  it('ask() replays a matching recorded session (fast mode, no real delay)', async () => {
    const idx = await ds.sessions()
    const session = idx.sessions[0]
    if (!session) throw new Error('expected at least one recorded session')
    const events = []
    for await (const ev of ds.ask(session.question, session.context, session.id)) {
      events.push(ev)
    }
    expect(events.length).toBeGreaterThan(0)
    expect(events.at(-1)?.type).toBe('answer')
  })

  it('ask() returns live_mode_required for an unrecognized free-text question', async () => {
    const events = []
    for await (const ev of ds.ask('some question nobody recorded', { screen: 'field' })) {
      events.push(ev)
    }
    expect(events).toHaveLength(1)
    const event = events[0]
    expect(event?.type === 'answer' && event.answer.kind).toBe('live_mode_required')
  })

  it('evalReport() and repro() validate', async () => {
    const ev = await ds.evalReport()
    expect(ev.gold_set.status).toBe('pending')
    const repro = await ds.repro()
    expect(repro.data_files.length).toBeGreaterThan(0)
  })

  it('a missing fixture file throws a readable StrataDataError naming the path', async () => {
    await expect(ds.kpis('not-a-real-well')).rejects.toMatchObject({
      name: 'StrataDataError',
      path: 'wells/not-a-real-well/kpis.json',
    })
  })

  it('the sparse well (15_9-F-5) still loads, with lower confidence', async () => {
    const kpis = await ds.kpis(SPARSE_WELL)
    expect(kpis.well).toBe(SPARSE_WELL)
  })
})
