// S6 Formation view — docs/06_SCREENS.md S6, comp S6-Formation.dc.html.
//
// MD scale, picked tops, predicted track (abstain/disagree patterns), lithology, the 5
// depth-indexed curve tracks, model card summary and per-formation table are built from real
// data where it exists (formations.json/formation_pred.json/depth_series.json, T11.1/T11.2).
// Offset compare (T11.4) and depth<->time linking (T11.5) are separate modules wired in here.
// The Events column and "Selected event" panel (T12.3) render T12.1/T12.2's real extracted
// issues + precursor windows — empty for any well those haven't found anything real for,
// never a placeholder event.
import { useMemo, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import type { FormationPrediction, FormationReport, Issue } from '../../contracts/types'
import {
  useDepthSeries,
  useDepthTime,
  useFormationPred,
  useFormations,
  useIssues,
  useModelCard,
  usePrecursors,
  useWells,
} from '../../data/hooks'
import { useView } from '../../state/view'
import { ConfidenceBadge } from '../../trust/ConfidenceBadge'
import { InsufficientData } from '../../trust/InsufficientData'
import { MockBadge } from '../../trust/MockBadge'
import { Num } from '../../trust/Num'
import { buildCurvePath, buildDepthTicks, colorForFormation, finiteRange, mdToY } from './depthScale'
import { mdIntervalToTimeWindow } from './depthTimeLink'
import { OffsetCompare } from './OffsetCompare'
import { buildPrecursorPaths } from './precursorChart'

const TRACK_HEIGHT = 720
const CURVES: { key: string; label: string }[] = [
  { key: 'ROP', label: 'ROP' },
  { key: 'MSE', label: 'MSE' },
  { key: 'DXC', label: 'd-exp' },
  { key: 'GAS', label: 'Gas' },
]

const ABSTAIN_PATTERN = 'repeating-linear-gradient(45deg,#3A4552 0 2px,#161D25 2px 6px)'

const EVENT_KEY: Record<string, string> = {
  stuck_pipe: 'SP', losses: 'LC', tight_hole: 'TH', kick: 'KC', pack_off: 'PO', washout: 'WO', other: 'OT',
}
const EVENT_COLOR: Record<string, string> = {
  stuck_pipe: 'var(--danger)', losses: '#7CC4FF', tight_hole: 'var(--accent)', kick: '#FF9A7A',
  pack_off: '#C9A7FF', washout: '#6FE3C2', other: 'var(--text-2)',
}

function TopsTrack({
  tops,
  mdMin,
  mdMax,
  onSelect,
}: {
  tops: FormationReport['tops']
  mdMin: number
  mdMax: number
  onSelect?: (mdTop: number, mdBase: number) => void
}) {
  return (
    <div style={{ position: 'relative', height: TRACK_HEIGHT }}>
      {tops.map((top) => {
        const y0 = mdToY(top.md_top, mdMin, mdMax, TRACK_HEIGHT)
        const y1 = mdToY(top.md_base, mdMin, mdMax, TRACK_HEIGHT)
        return (
          <button
            key={`${top.name}-${top.md_top}`}
            type="button"
            onClick={() => onSelect?.(top.md_top, top.md_base)}
            title={`${top.name} — open this depth window in Workspace`}
            className="absolute right-0 left-0 box-border overflow-hidden border-0 px-1.5 py-1 text-left"
            style={{ top: y0, height: Math.max(0, y1 - y0), background: colorForFormation(top.name), cursor: onSelect ? 'pointer' : 'default' }}
          >
            <span className="text-[11.5px] font-semibold" style={{ color: '#0A0E13' }}>
              {top.name}
            </span>
          </button>
        )
      })}
    </div>
  )
}

function PredictedTrack({
  intervals,
  mdMin,
  mdMax,
  onSelect,
}: {
  intervals: FormationPrediction['intervals']
  mdMin: number
  mdMax: number
  onSelect?: (mdTop: number, mdBase: number) => void
}) {
  return (
    <div style={{ position: 'relative', height: TRACK_HEIGHT }}>
      {intervals.map((iv) => {
        const y0 = mdToY(iv.md_top, mdMin, mdMax, TRACK_HEIGHT)
        const y1 = mdToY(iv.md_base, mdMin, mdMax, TRACK_HEIGHT)
        const disagrees = iv.agrees_with_pick === false
        const bg = iv.abstained ? ABSTAIN_PATTERN : disagrees ? 'var(--danger)' : colorForFormation(iv.label ?? '')
        const fg = iv.abstained ? 'var(--text)' : '#0A0E13'
        const title = iv.abstained
          ? `Abstained (p=${iv.p.toFixed(2)} below threshold) — open this depth window in Workspace`
          : disagrees
            ? `Disagrees with picked top (p=${iv.p.toFixed(2)}) — open this depth window in Workspace`
            : `${iv.label} (p=${iv.p.toFixed(2)}) — open this depth window in Workspace`
        return (
          <button
            key={`${iv.md_top}-${iv.md_base}`}
            type="button"
            onClick={() => onSelect?.(iv.md_top, iv.md_base)}
            title={title}
            className="absolute right-0 left-0 box-border flex items-center justify-between overflow-hidden border-0 px-1.5 py-1 text-left"
            style={{ top: y0, height: Math.max(0, y1 - y0), background: bg, cursor: onSelect ? 'pointer' : 'default' }}
          >
            <span className="text-[11px] font-semibold" style={{ color: fg }}>
              {iv.abstained ? 'abstain' : iv.label}
            </span>
            {!iv.abstained && (
              <span className="font-mono text-[10.5px]" style={{ color: fg }}>
                {iv.p.toFixed(2)}
              </span>
            )}
          </button>
        )
      })}
    </div>
  )
}

function LithologyTrack({ lithology, mdMin, mdMax }: { lithology: FormationReport['lithology']; mdMin: number; mdMax: number }) {
  const LITH_COLOR: Record<string, string> = {
    sandstone: '#E8D27A',
    shale: '#8F8F8F',
    claystone: '#B0A08A',
    limestone: '#A7C4A0',
    marl: '#C9A97A',
    coal: '#3A3A3A',
    granite: '#C98A6A',
    other: '#5D6D7E',
  }
  return (
    <div style={{ position: 'relative', height: TRACK_HEIGHT }}>
      {lithology.map((l) => {
        const y0 = mdToY(l.md_top, mdMin, mdMax, TRACK_HEIGHT)
        const y1 = mdToY(l.md_base, mdMin, mdMax, TRACK_HEIGHT)
        return (
          <div
            key={`${l.md_top}-${l.md_base}`}
            title={l.lith}
            className="absolute right-0 left-0"
            style={{ top: y0, height: Math.max(0, y1 - y0), background: LITH_COLOR[l.lith] ?? LITH_COLOR.other }}
          />
        )
      })}
    </div>
  )
}

function EventsTrack({
  issues,
  mdMin,
  mdMax,
  selectedId,
  onSelect,
}: {
  issues: Issue[]
  mdMin: number
  mdMax: number
  selectedId: string | null
  onSelect: (id: string) => void
}) {
  return (
    <div style={{ position: 'relative', height: TRACK_HEIGHT }}>
      {issues
        .filter((i): i is Issue & { md: number } => i.md !== null && i.md !== undefined)
        .map((issue) => {
          const y = mdToY(issue.md, mdMin, mdMax, TRACK_HEIGHT)
          const selected = issue.id === selectedId
          const color = EVENT_COLOR[issue.type] ?? EVENT_COLOR.other
          return (
            <button
              key={issue.id}
              type="button"
              onClick={() => onSelect(issue.id)}
              aria-pressed={selected}
              aria-label={`${issue.type.replace('_', ' ')} at ${issue.md} m — ${issue.excerpt.slice(0, 80)}`}
              title={`${issue.type.replace('_', ' ')} at ${issue.md} m`}
              className="absolute left-2 h-[22px] w-[22px] rounded border-2 font-mono text-[10px] font-bold"
              style={{
                top: y - 11,
                borderColor: selected ? 'var(--text)' : color,
                background: color,
                color: '#0A0E13',
                cursor: 'pointer',
              }}
            >
              {EVENT_KEY[issue.type] ?? '?'}
            </button>
          )
        })}
    </div>
  )
}

function PrecursorSparkline({ channel }: { channel: { channel: string; unit: string; value: (number | null)[]; band_lo: (number | null)[]; band_hi: (number | null)[] } }) {
  const { line, band } = buildPrecursorPaths(channel.value, channel.band_lo, channel.band_hi)
  return (
    <div className="flex flex-col gap-0.5">
      <div className="flex justify-between text-meta">
        <span>{channel.channel}</span>
        <span className="font-mono text-text-2">{channel.unit}</span>
      </div>
      <svg
        viewBox="0 0 300 48"
        preserveAspectRatio="none"
        style={{ width: '100%', height: 48, display: 'block', background: 'var(--bg-nav)', borderRadius: 3 }}
      >
        {band && <path d={band} fill="rgba(124,196,255,.16)" />}
        {line && <path d={line} fill="none" stroke="var(--text)" strokeWidth={1.5} vectorEffect="non-scaling-stroke" />}
        <line x1="299" y1="0" x2="299" y2="48" stroke="var(--danger)" strokeWidth={2} vectorEffect="non-scaling-stroke" />
      </svg>
    </div>
  )
}

function CurveTrack({
  label,
  unit,
  md,
  values,
  secondaryValues,
}: {
  label: string
  unit: string
  md: number[]
  values: (number | null)[]
  secondaryValues?: (number | null)[]
}) {
  const mdMin = md[0] ?? 0
  const mdMax = md[md.length - 1] ?? 1
  const range = finiteRange(values) ?? [0, 1]
  const path = buildCurvePath(md, values, mdMin, mdMax, TRACK_HEIGHT, range[0], range[1])
  const path2 = secondaryValues ? buildCurvePath(md, secondaryValues, mdMin, mdMax, TRACK_HEIGHT, range[0], range[1]) : ''

  return (
    <div className="flex min-w-0 flex-col" style={{ borderLeft: '1px solid var(--line-soft)' }}>
      <div className="flex h-[46px] flex-col justify-end gap-0.5 border-b px-2 py-1.5" style={{ borderColor: 'var(--line)' }}>
        <span className="font-condensed text-label uppercase text-text-3">{label}</span>
        <span className="font-mono text-[11px] text-text-3">{unit}</span>
      </div>
      <div style={{ position: 'relative', height: TRACK_HEIGHT }}>
        <svg
          viewBox={`0 0 100 ${TRACK_HEIGHT}`}
          preserveAspectRatio="none"
          style={{ width: '100%', height: '100%', display: 'block' }}
        >
          <path d={path} fill="none" stroke="var(--accent)" strokeWidth={1.3} vectorEffect="non-scaling-stroke" />
          {path2 && (
            <path
              d={path2}
              fill="none"
              stroke="var(--link)"
              strokeWidth={1.3}
              strokeDasharray="4 3"
              vectorEffect="non-scaling-stroke"
            />
          )}
        </svg>
      </div>
    </div>
  )
}

function PerFormationTable({ stats }: { stats: FormationReport['stats'] }) {
  return (
    <section
      className="flex flex-col gap-2.5 overflow-x-auto rounded border p-4"
      style={{ borderColor: 'var(--line)', background: 'var(--panel)' }}
    >
      <span className="font-condensed text-label uppercase text-text-3">Per-formation summary</span>
      <table className="w-full min-w-[760px] border-collapse text-dense">
        <thead>
          <tr className="font-condensed text-left text-label uppercase text-text-3">
            <th className="border-b px-2 py-2" style={{ borderColor: 'var(--line)' }}>
              Formation
            </th>
            <th className="border-b px-2 py-2" style={{ borderColor: 'var(--line)' }}>
              Avg ROP
            </th>
            <th className="border-b px-2 py-2" style={{ borderColor: 'var(--line)' }}>
              Avg MSE
            </th>
            <th className="border-b px-2 py-2" style={{ borderColor: 'var(--line)' }}>
              Incidents
            </th>
            <th className="border-b px-2 py-2" style={{ borderColor: 'var(--line)' }}>
              Wells
            </th>
            <th className="border-b px-2 py-2" style={{ borderColor: 'var(--line)' }}>
              Confidence
            </th>
          </tr>
        </thead>
        <tbody>
          {stats.map((s) => (
            <tr key={s.formation} className="font-mono">
              <td className="border-b px-2 py-2 font-sans" style={{ borderColor: 'var(--line-soft)' }}>
                {s.formation}
              </td>
              <td className="border-b px-2 py-2" style={{ borderColor: 'var(--line-soft)' }}>
                <Num q={s.avg_rop} />
              </td>
              <td className="border-b px-2 py-2" style={{ borderColor: 'var(--line-soft)' }}>
                <Num q={s.avg_mse} />
              </td>
              <td className="border-b px-2 py-2" style={{ borderColor: 'var(--line-soft)' }}>
                {s.incidents}
              </td>
              <td className="border-b px-2 py-2" style={{ borderColor: 'var(--line-soft)' }}>
                {s.n_wells}
              </td>
              <td className="border-b px-2 py-2" style={{ borderColor: 'var(--line-soft)' }}>
                <ConfidenceBadge c={s.confidence} />
              </td>
            </tr>
          ))}
        </tbody>
      </table>
      <p className="m-0 text-label text-text-2">
        &quot;Best parameter window&quot; (advisory, not shown — no offset-well analysis yet, T11.4) would be a
        descriptive statistic from offset wells, never a setpoint.
      </p>
    </section>
  )
}

export function S6Formation() {
  const { id: wellId } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const [viewMode, setViewMode] = useState<'single' | 'offset'>('single')
  const wells = useWells()
  const wellSummary = wells.data?.wells.find((w) => w.id === wellId)
  const formations = useFormations(wellId)
  const formationPred = useFormationPred(wellId)
  const depthSeries = useDepthSeries(wellId)
  const depthTime = useDepthTime(wellId)
  const modelCard = useModelCard('formation')
  const issues = useIssues({ well: wellId })
  const [selectedIssueId, setSelectedIssueId] = useState<string | null>(null)
  const precursors = usePrecursors(selectedIssueId ?? undefined)
  const setDepthRange = useView((s) => s.setDepthRange)
  const setCopilotPrefill = useView((s) => s.setCopilotPrefill)
  const setPanel = useView((s) => s.setPanel)
  const [briefFormation, setBriefFormation] = useState<string | null>(null)

  const selectedIssue = issues.data?.find((i) => i.id === selectedIssueId) ?? null

  function openIntervalInWorkspace(mdTop: number, mdBase: number) {
    if (!depthTime.data || !wellId) return
    const window = mdIntervalToTimeWindow(depthTime.data, mdTop, mdBase)
    if (!window) return
    navigate(`/well/${wellId}/workspace?t0=${window.t0}&t1=${window.t1}`)
  }

  function openIssueInWorkspace(issue: Issue) {
    const t1 = issue.t1 ?? issue.t0 + 600_000
    navigate(`/well/${wellId}/workspace?t0=${issue.t0}&t1=${t1}`)
  }

  function askCopilotAboutIssue(issue: Issue) {
    setCopilotPrefill(
      `Why did this ${issue.type.replace('_', ' ')} happen at ${issue.md ?? '—'} m in ${wellSummary?.name ?? wellId}? ` +
        `DDR excerpt: "${issue.excerpt}"`,
    )
    setPanel('copilot')
  }

  function generateFormationBrief(formationName: string) {
    if (!wellSummary || !formations.data) return
    const top = formations.data.tops.find((t) => t.name === formationName)
    if (top) setDepthRange([top.md_top, top.md_base])
    setCopilotPrefill(
      `Pre-spud brief: ${formationName} — summarize ROP, MSE and any known issues before drilling ` +
        `into it in ${wellSummary.name}.`,
    )
    setPanel('copilot')
  }

  const md = depthSeries.data?.md ?? []
  const mdMin = md[0] ?? 0
  const mdMax = md[md.length - 1] ?? 1

  const mwValues = depthSeries.data?.channels.MW_IN?.values
  const ecdValues = depthSeries.data?.channels.ECD?.values

  const curveTracks = useMemo(() => {
    if (!depthSeries.data) return []
    const base = CURVES.map((c) => ({
      label: c.label,
      unit: depthSeries.data?.channels[c.key]?.unit ?? '1',
      values: depthSeries.data?.channels[c.key]?.values ?? [],
    }))
    return [
      ...base,
      {
        label: 'MW · ECD',
        unit: depthSeries.data.channels.MW_IN?.unit ?? 'sg',
        values: mwValues ?? [],
        secondaryValues: ecdValues ?? [],
      },
    ]
  }, [depthSeries.data, mwValues, ecdValues])

  if (!wellId) return <InsufficientData reason="No well selected." />
  if (wells.isLoading) return <div className="p-6 text-text-2">Loading…</div>
  if (!wellSummary) {
    return <InsufficientData reason={`No well named "${wellId}" was found in this export.`} />
  }
  if (formations.isLoading || depthSeries.isLoading) {
    return <div className="p-6 text-text-2">Loading…</div>
  }
  if (!formations.data || !depthSeries.data) {
    return (
      <main className="mx-auto max-w-[1360px] p-6">
        <InsufficientData
          reason={`${wellSummary.name} has no formation/depth-series export yet — this well doesn't have a dense channel series (only ${wellSummary.name} and a couple of other detailed wells currently do, see tasks/BACKLOG.md T11.2).`}
        />
      </main>
    )
  }

  return (
    <main className="mx-auto flex w-full max-w-[1360px] flex-col gap-4 px-6 py-6">
      <div className="flex flex-wrap items-center gap-2.5">
        <h1 className="m-0 font-mono text-[20px] font-medium">{wellSummary.name}</h1>
        <span className="font-condensed text-label uppercase text-text-3">
          Depth view · {Math.round(mdMin).toLocaleString('en-US')} – {Math.round(mdMax).toLocaleString('en-US')} m MD
        </span>
        <div className="ml-auto flex flex-wrap items-center gap-1.5">
          <button
            type="button"
            onClick={() => setViewMode('single')}
            aria-pressed={viewMode === 'single'}
            className="min-h-9 rounded border px-3.5 text-dense"
            style={{ borderColor: viewMode === 'single' ? 'var(--accent)' : 'var(--line)', background: 'var(--panel)' }}
          >
            Single well
          </button>
          <button
            type="button"
            onClick={() => setViewMode('offset')}
            aria-pressed={viewMode === 'offset'}
            className="min-h-9 rounded border px-3.5 text-dense"
            style={{ borderColor: viewMode === 'offset' ? 'var(--accent)' : 'var(--line)', background: 'var(--panel)' }}
          >
            Offset compare
          </button>
          {formations.data && formations.data.stats.length > 0 && (
            <select
              aria-label="Formation for the generated brief"
              className="min-h-9 rounded border px-2 text-dense"
              style={{ borderColor: 'var(--line)', background: 'var(--panel)' }}
              value={briefFormation ?? formations.data.stats[0]?.formation ?? ''}
              onChange={(e) => setBriefFormation(e.target.value)}
            >
              {formations.data.stats.map((s) => (
                <option key={s.formation} value={s.formation}>
                  {s.formation}
                </option>
              ))}
            </select>
          )}
          <button
            type="button"
            disabled={!formations.data || formations.data.stats.length === 0}
            onClick={() =>
              generateFormationBrief(briefFormation ?? formations.data?.stats[0]?.formation ?? '')
            }
            className="min-h-9 rounded border px-3.5 text-dense disabled:opacity-50"
            style={{ borderColor: 'var(--accent)', background: 'var(--mock-bg)', color: 'var(--mock-fg)' }}
            title="Opens the copilot with a pre-spud brief question for the selected formation"
          >
            Generate formation brief
          </button>
          {wellSummary.is_mock && <MockBadge />}
        </div>
      </div>

      {viewMode === 'offset' && <OffsetCompare wells={wells.data?.wells ?? []} initialWellId={wellId} />}

      {viewMode === 'single' && (
      <div className="flex flex-wrap items-start gap-4">
        <section
          className="min-w-0 flex-[999_1_720px] overflow-x-auto rounded border"
          style={{ borderColor: 'var(--line)', background: 'var(--panel)' }}
        >
          <div
            className="relative grid min-w-[980px]"
            style={{ gridTemplateColumns: `64px 140px 140px 60px repeat(${curveTracks.length}, minmax(90px, 1fr)) 48px` }}
          >
            <div className="flex min-w-0 flex-col">
              <div className="flex h-[46px] flex-col justify-end gap-0.5 border-b px-2 py-1.5" style={{ borderColor: 'var(--line)' }}>
                <span className="font-condensed text-label uppercase text-text-3">MD</span>
                <span className="font-mono text-[11px] text-text-3">m</span>
              </div>
              <div style={{ position: 'relative', height: TRACK_HEIGHT }}>
                {buildDepthTicks(mdMin, mdMax, TRACK_HEIGHT).map((t) => (
                  <span
                    key={t.label}
                    className="absolute right-2 font-mono text-[11px] text-text-3"
                    style={{ top: t.y }}
                  >
                    {t.label}
                  </span>
                ))}
              </div>
            </div>

            <div className="flex min-w-0 flex-col" style={{ borderLeft: '1px solid var(--line-soft)' }}>
              <div className="flex h-[46px] flex-col justify-end gap-0.5 border-b px-2 py-1.5" style={{ borderColor: 'var(--line)' }}>
                <span className="font-condensed text-label uppercase text-text-3">Tops · picked</span>
              </div>
              <TopsTrack tops={formations.data.tops} mdMin={mdMin} mdMax={mdMax} onSelect={openIntervalInWorkspace} />
            </div>

            <div className="flex min-w-0 flex-col" style={{ borderLeft: '1px solid var(--line-soft)' }}>
              <div className="flex h-[46px] flex-col justify-end gap-0.5 border-b px-2 py-1.5" style={{ borderColor: 'var(--line)' }}>
                <span className="font-condensed text-label uppercase" style={{ color: 'var(--mock-fg)' }}>
                  Predicted · PR-3
                </span>
                <span className="font-mono text-[11px] text-text-3">LOWO model</span>
              </div>
              {formationPred.data ? (
                <PredictedTrack
                  intervals={formationPred.data.intervals}
                  mdMin={mdMin}
                  mdMax={mdMax}
                  onSelect={openIntervalInWorkspace}
                />
              ) : (
                <div className="p-2 text-label text-text-2">No trained prediction for this well yet.</div>
              )}
            </div>

            <div className="flex min-w-0 flex-col" style={{ borderLeft: '1px solid var(--line-soft)' }}>
              <div className="flex h-[46px] flex-col justify-end gap-0.5 border-b px-2 py-1.5" style={{ borderColor: 'var(--line)' }}>
                <span className="font-condensed text-label uppercase text-text-3">Lith.</span>
              </div>
              <LithologyTrack lithology={formations.data.lithology} mdMin={mdMin} mdMax={mdMax} />
            </div>

            {curveTracks.map((c) => (
              <CurveTrack key={c.label} label={c.label} unit={c.unit} md={md} values={c.values} secondaryValues={c.secondaryValues} />
            ))}

            <div className="flex min-w-0 flex-col" style={{ borderLeft: '1px solid var(--line-soft)' }}>
              <div className="flex h-[46px] flex-col justify-end gap-0.5 border-b px-2 py-1.5" style={{ borderColor: 'var(--line)' }}>
                <span className="font-condensed text-label uppercase text-text-3">Events</span>
              </div>
              <EventsTrack
                issues={issues.data ?? []}
                mdMin={mdMin}
                mdMax={mdMax}
                selectedId={selectedIssueId}
                onSelect={setSelectedIssueId}
              />
            </div>
          </div>

          <div
            className="flex flex-wrap gap-2 border-t px-3.5 py-2.5 text-label text-text-2"
            style={{ borderColor: 'var(--line)' }}
          >
            <span className="inline-flex items-center gap-1.5">
              <span className="inline-block h-2.5 w-4" style={{ background: ABSTAIN_PATTERN }} />
              Abstained (p &lt; threshold)
            </span>
            <span className="inline-flex items-center gap-1.5">
              <span className="inline-block h-2.5 w-4" style={{ background: 'var(--danger)' }} />
              Disagrees with pick
            </span>
            <span>Dashed curve = ECD next to mud weight</span>
            <span>
              Event keys: <span className="font-mono">SP</span> stuck pipe · <span className="font-mono">LC</span>{' '}
              losses · <span className="font-mono">TH</span> tight hole · <span className="font-mono">KC</span> kick
            </span>
          </div>
        </section>

        <aside className="flex min-w-0 flex-[1_1_380px] flex-col gap-3.5">
          <section
            className="flex flex-col gap-2.5 rounded border p-4"
            style={{ borderColor: selectedIssue ? 'var(--danger)' : 'var(--line)', background: 'var(--panel)' }}
          >
            <span className="font-condensed text-label uppercase text-text-3">Selected event</span>
            {!selectedIssue ? (
              <InsufficientData
                reason={
                  (issues.data?.length ?? 0) > 0
                    ? 'Click an event marker in the Events column to see its detail.'
                    : 'No DDR events extracted for this well yet (T12.1 found none here).'
                }
              />
            ) : (
              <>
                <div className="flex flex-wrap items-baseline justify-between gap-2">
                  <span className="text-label" style={{ color: EVENT_COLOR[selectedIssue.type] ?? EVENT_COLOR.other }}>
                    {EVENT_KEY[selectedIssue.type] ?? '?'} · {selectedIssue.type.replace('_', ' ')} ·{' '}
                    {selectedIssue.md ?? '—'} m
                  </span>
                  {selectedIssue.duration && <Num q={selectedIssue.duration} />}
                </div>
                <blockquote
                  className="m-0 border-l-2 pl-2.5 text-dense italic"
                  style={{ borderColor: 'var(--line)', color: 'var(--text-2)' }}
                >
                  &ldquo;{selectedIssue.excerpt}&rdquo;
                  <span className="mt-1 block font-mono text-meta not-italic text-text-3">
                    DDR {selectedIssue.report_date}
                  </span>
                </blockquote>
                <span className="font-condensed text-label uppercase text-text-3">
                  Precursor signature · 6h before event
                </span>
                {precursors.data ? (
                  <>
                    {precursors.data.channels.map((c) => (
                      <PrecursorSparkline key={c.channel} channel={c} />
                    ))}
                    <p className="m-0 text-meta text-text-2">{precursors.data.baseline_note}</p>
                  </>
                ) : (
                  <p className="m-0 text-label text-text-2">
                    No precursor window available for this event (needs an MD and overlapping time-series
                    data).
                  </p>
                )}
                <div className="flex flex-wrap gap-2">
                  <button
                    type="button"
                    onClick={() => openIssueInWorkspace(selectedIssue)}
                    className="min-h-8 rounded border px-2.5 text-label"
                    style={{ borderColor: 'var(--line)', background: 'var(--panel-2)' }}
                  >
                    Open window in Workspace
                  </button>
                  <button
                    type="button"
                    onClick={() => askCopilotAboutIssue(selectedIssue)}
                    className="min-h-8 rounded border px-2.5 text-label"
                    style={{ borderColor: 'var(--line)', background: 'var(--panel-2)' }}
                  >
                    Ask copilot
                  </button>
                </div>
              </>
            )}
          </section>

          <section className="flex flex-col gap-2 rounded border p-4" style={{ borderColor: 'var(--line)', background: 'var(--panel)' }}>
            <div className="flex flex-wrap items-baseline justify-between gap-2">
              <span className="font-condensed text-label uppercase text-text-3">Formation classifier · model card</span>
              <a href="/trust" className="text-meta text-link">
                Full card →
              </a>
            </div>
            {modelCard.data ? (
              <pre className="m-0 whitespace-pre-wrap font-mono text-label leading-relaxed text-text-2">
                {`validation   ${modelCard.data.validation}\nwells        ${modelCard.data.n_wells ?? '—'}\nmetrics      ${Object.entries(
                  modelCard.data.metrics,
                )
                  .map(([k, v]) => `${k}=${v?.value ?? '—'}`)
                  .join(', ')}`}
              </pre>
            ) : (
              <p className="m-0 text-label text-text-2">
                No formation model card export yet — a real leave-one-well-out run is blocked on this dev
                machine's available RAM (tasks/BACKLOG.md T11.2).
              </p>
            )}
          </section>
        </aside>
      </div>
      )}

      {viewMode === 'single' && <PerFormationTable stats={formations.data.stats} />}
    </main>
  )
}
