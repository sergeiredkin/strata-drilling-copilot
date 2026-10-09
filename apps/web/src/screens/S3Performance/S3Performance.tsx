// S3 Performance & invisible lost time — docs/06_SCREENS.md S3, comp S3-Performance.dc.html.
import { useMemo } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { ByDay } from '../../charts/echarts/ByDay'
import { KpiDist } from '../../charts/echarts/KpiDist'
import { Waterfall } from '../../charts/echarts/Waterfall'
import { useIlt, useKpis, useWells } from '../../data/hooks'
import { useView } from '../../state/view'
import { ConfidenceBadge } from '../../trust/ConfidenceBadge'
import { InsufficientData } from '../../trust/InsufficientData'
import { MockBadge } from '../../trust/MockBadge'
import { Num } from '../../trust/Num'
import { buildDisplayCards } from './kpiCards'

const ILT_CATEGORY_LABEL: Record<string, string> = {
  connections: 'Connections',
  trips: 'Trips',
  flat_time: 'Flat time',
  unreported_reaming: 'Reaming (unreported)',
}
const ILT_CATEGORY_COLOR: Record<string, string> = {
  connections: '#E39A1E',
  trips: '#9670E0',
  flat_time: '#5E7387',
  unreported_reaming: '#2A9C7E',
}

export function S3Performance() {
  const { id: wellId } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const section = useView((s) => s.section)
  const setSection = useView((s) => s.setSection)

  const wells = useWells()
  const wellSummary = wells.data?.wells.find((w) => w.id === wellId)
  const kpis = useKpis(wellId)
  const ilt = useIlt(wellId)

  const displayCards = useMemo(() => (kpis.data ? buildDisplayCards(kpis.data) : []), [kpis.data])
  const connDistAll = useMemo(
    () => kpis.data?.distributions.filter((d) => d.kpi === 'conn_s2s') ?? [],
    [kpis.data],
  )
  const availableSections = useMemo(
    () => [...new Set(connDistAll.map((d) => d.section))],
    [connDistAll],
  )
  const connDist = section ? connDistAll.filter((d) => d.section === section) : connDistAll

  function openWorkspaceAt(t0: number, t1: number) {
    navigate(`/well/${wellId}/workspace?t0=${t0}&t1=${t1}`)
  }

  if (!wellId) return <InsufficientData reason="No well selected." />
  if (wells.isLoading || kpis.isLoading || ilt.isLoading) {
    return <div className="p-6 text-text-2">Loading…</div>
  }
  if (!wellSummary) {
    return <InsufficientData reason={`No well named "${wellId}" was found in this export.`} />
  }
  if (!kpis.data || !ilt.data) {
    return (
      <main className="mx-auto max-w-[1360px] p-6">
        <InsufficientData reason={`${wellSummary.name} has no KPI/ILT export yet.`} />
      </main>
    )
  }

  const tripInOpenCard = kpis.data.cards.find((c) => c.kpi === 'trip_in_open')
  const tripOutOpenCard = kpis.data.cards.find((c) => c.kpi === 'trip_out_open')
  const connW2wCard = kpis.data.cards.find((c) => c.kpi === 'conn_w2w')

  return (
    <main className="mx-auto flex w-full max-w-[1360px] flex-col gap-5 px-6 py-6">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div className="flex flex-col gap-1">
          <h1 className="m-0 text-page-title font-semibold">Performance & invisible lost time</h1>
          <p className="m-0 text-body text-text-2">
            <span className="font-mono">{wellSummary.name}</span> · {section ?? 'all sections'} ·
            composite best = best 10% of connections and stands
          </p>
        </div>
        <div className="flex flex-wrap items-center gap-1.5">
          <button
            type="button"
            onClick={() => setSection(null)}
            aria-pressed={!section}
            className="min-h-9 rounded border px-3.5 text-dense"
            style={{ borderColor: !section ? 'var(--accent)' : 'var(--line)', background: 'var(--panel)' }}
          >
            All sections
          </button>
          {availableSections.map((s) => (
            <button
              key={s}
              type="button"
              onClick={() => setSection(s)}
              aria-pressed={section === s}
              className="min-h-9 rounded border px-3.5 text-dense"
              style={{ borderColor: section === s ? 'var(--accent)' : 'var(--line)', background: 'var(--panel)' }}
            >
              {s}
            </button>
          ))}
          <MockBadge />
        </div>
      </div>

      <div className="grid grid-cols-[repeat(auto-fit,minmax(240px,1fr))] gap-3.5">
        {displayCards.map((card) => (
          <div key={card.name} className="flex flex-col gap-2 rounded border p-4" style={{ borderColor: 'var(--line)', background: 'var(--panel)' }}>
            <span className="font-condensed text-label uppercase text-text-3">{card.name}</span>
            <Num q={card.value} kind="kpi" />
            <div className="text-meta text-text-2">
              {card.subKpi === 'static' && card.subStatic}
              {card.subKpi === 'conn_w2w' && connW2wCard && (
                <>
                  slips-to-slips · weight-to-weight <Num q={connW2wCard.value} />
                </>
              )}
              {card.subKpi === 'trip_cased' && (
                <>
                  in: cased {'—'} · open {tripInOpenCard ? <Num q={tripInOpenCard.value} /> : '—'} · out:
                  cased {'—'} · open {tripOutOpenCard ? <Num q={tripOutOpenCard.value} /> : '—'}
                </>
              )}
            </div>
            <div className="flex items-center justify-between border-t pt-2" style={{ borderColor: 'var(--line-soft)' }}>
              <span className="font-mono text-meta" style={{ color: 'var(--ok)' }}>
                best {card.best ? <Num q={card.best} /> : '—'}
              </span>
              <ConfidenceBadge c={card.confidence} />
            </div>
          </div>
        ))}
      </div>

      <div className="flex flex-wrap gap-4">
        <section className="flex min-w-0 flex-[3_1_560px] flex-col gap-3.5 rounded border p-4.5" style={{ borderColor: 'var(--line)', background: 'var(--panel)' }}>
          <div className="flex flex-wrap justify-between gap-2">
            <span className="font-condensed text-label uppercase text-text-3">
              Connection time distribution · slips-to-slips
            </span>
            <span className="text-meta text-text-2">{'●'} outlier — click to open in Workspace</span>
          </div>
          {connDist.length > 0 ? (
            <KpiDist
              rows={connDist}
              unit="min"
              onOutlierClick={(_sec, t0, t1) => openWorkspaceAt(t0 - 2 * 60_000, t1 + 2 * 60_000)}
            />
          ) : (
            <InsufficientData reason="No connection-time distribution for this section." />
          )}
        </section>

        <section className="flex min-w-0 flex-[2_1_380px] flex-col gap-3" style={{ borderColor: 'var(--line)', background: 'var(--panel)' }}>
          <div className="flex h-full flex-col gap-3 rounded border p-4.5" style={{ borderColor: 'var(--line)', background: 'var(--panel)' }}>
            <span className="font-condensed text-label uppercase text-text-3">Lost time vs composite best</span>
            <div className="flex items-baseline gap-2">
              <Num q={ilt.data.total} kind="kpi" />
              <span className="ml-auto font-mono text-meta text-text-2">
                <Num q={ilt.data.booked_npt} /> booked as NPT in DDR
              </span>
            </div>
            <Waterfall
              items={ilt.data.by_category.map((c) => ({
                name: ILT_CATEGORY_LABEL[c.category] ?? c.category,
                hours: c.hours.value ?? 0,
                color: ILT_CATEGORY_COLOR[c.category] ?? '#5E7387',
              }))}
              total={ilt.data.total.value ?? 0}
            />
          </div>
        </section>
      </div>

      <div className="flex flex-wrap gap-4">
        <section className="min-w-0 flex-[1_1_520px] overflow-x-auto rounded border p-4.5" style={{ borderColor: 'var(--line)', background: 'var(--panel)' }}>
          <span className="font-condensed text-label uppercase text-text-3">By hole section</span>
          <table className="mt-2 w-full min-w-[480px] border-collapse text-dense">
            <thead>
              <tr className="font-condensed text-label uppercase text-text-3">
                <th className="border-b px-2 py-2 text-left" style={{ borderColor: 'var(--line)' }}>Section</th>
                <th className="border-b px-2 py-2 text-left" style={{ borderColor: 'var(--line)' }}>Connections</th>
                <th className="border-b px-2 py-2 text-left" style={{ borderColor: 'var(--line)' }}>Trips</th>
                <th className="border-b px-2 py-2 text-left" style={{ borderColor: 'var(--line)' }}>Flat time</th>
                <th className="border-b px-2 py-2 text-left" style={{ borderColor: 'var(--line)' }}>Reaming</th>
                <th className="border-b px-2 py-2 text-left" style={{ borderColor: 'var(--line)' }}>Total h</th>
              </tr>
            </thead>
            <tbody>
              {ilt.data.by_section.map((row) => (
                <tr key={row.section} className="font-mono">
                  <td className="border-b px-2 py-2" style={{ borderColor: 'var(--line-soft)' }}>{row.section}</td>
                  <td className="border-b px-2 py-2" style={{ borderColor: 'var(--line-soft)' }}>
                    {row.by_category.connections ? <Num q={row.by_category.connections} /> : '—'}
                  </td>
                  <td className="border-b px-2 py-2" style={{ borderColor: 'var(--line-soft)' }}>
                    {row.by_category.trips ? <Num q={row.by_category.trips} /> : '—'}
                  </td>
                  <td className="border-b px-2 py-2" style={{ borderColor: 'var(--line-soft)' }}>
                    {row.by_category.flat_time ? <Num q={row.by_category.flat_time} /> : '—'}
                  </td>
                  <td className="border-b px-2 py-2" style={{ borderColor: 'var(--line-soft)' }}>
                    {row.by_category.unreported_reaming ? <Num q={row.by_category.unreported_reaming} /> : '—'}
                  </td>
                  <td className="border-b px-2 py-2" style={{ borderColor: 'var(--line-soft)', color: 'var(--mock-fg)' }}>
                    <Num q={row.total} />
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </section>

        <section className="min-w-0 flex-[1_1_520px] rounded border p-4.5" style={{ borderColor: 'var(--line)', background: 'var(--panel)' }}>
          <span className="font-condensed text-label uppercase text-text-3">By day · lost hours</span>
          <ByDay
            rows={ilt.data.by_day.map((d) => ({ date: d.date, hours: d.hours.value ?? 0, coveragePct: d.coverage_pct }))}
            onBarClick={(date) => {
              const t0 = new Date(`${date}T00:00:00Z`).getTime()
              openWorkspaceAt(t0, t0 + 24 * 3600 * 1000)
            }}
          />
          <p className="mt-2 text-meta text-text-2">
            Hatched day = &lt; 60% sensor coverage; its value is shown but excluded from the composite best.
          </p>
        </section>
      </div>
    </main>
  )
}
