// Connection-time (or any KPI) box plot per section, composite-best dashed line, clickable
// outliers — comp S3-Performance.dc.html. Horizontal boxplot (section = category/y-axis).
import ReactECharts from 'echarts-for-react'
import { useMemo } from 'react'
import type { Distribution } from '../../contracts/types'

export type KpiDistRow = { section: string; dist: Distribution }

function cssVar(name: string, fallback: string): string {
  if (typeof window === 'undefined') return fallback
  return getComputedStyle(document.documentElement).getPropertyValue(name).trim() || fallback
}

export function KpiDist({
  rows,
  unit,
  onOutlierClick,
}: {
  rows: KpiDistRow[]
  unit: string
  onOutlierClick?: (section: string, t0: number, t1: number) => void
}) {
  const option = useMemo(() => {
    const text2 = cssVar('--text-2', '#A9B6C3')
    const line = cssVar('--line', '#243040')
    const link = cssVar('--link', '#7CC4FF')
    const ok = cssVar('--ok', '#3DDC97')
    const danger = cssVar('--danger', '#FF9A7A')

    const sections = rows.map((r) => r.section)
    const boxData = rows.map((r) => {
      const d = r.dist
      return [d.min.value ?? 0, d.q1.value ?? 0, d.median.value ?? 0, d.q3.value ?? 0, d.max.value ?? 0]
    })
    const outlierData = rows.flatMap((r, i) =>
      (r.dist.outliers ?? []).map((o) => ({
        value: [i, o.value.value ?? 0],
        t0: o.t0,
        t1: o.t1,
        section: r.section,
      })),
    )
    const overallBest = rows.length > 0 ? (rows[0]?.dist.composite_best.value ?? null) : null

    return {
      backgroundColor: 'transparent',
      animation: false,
      grid: { left: 70, right: 24, top: 16, bottom: 28 },
      xAxis: {
        type: 'value',
        name: unit,
        nameLocation: 'end',
        axisLine: { lineStyle: { color: text2 } },
        axisLabel: { color: text2 },
        splitLine: { lineStyle: { color: line } },
      },
      yAxis: {
        type: 'category',
        data: sections,
        axisLine: { lineStyle: { color: text2 } },
        axisLabel: { color: text2, fontFamily: 'IBM Plex Mono, monospace' },
      },
      series: [
        {
          name: 'distribution',
          type: 'boxplot',
          data: boxData,
          itemStyle: { borderColor: link, color: 'rgba(124,196,255,.18)' },
        },
        {
          name: 'outliers',
          type: 'scatter',
          data: outlierData,
          symbolSize: 10,
          itemStyle: { color: danger, borderColor: cssVar('--bg', '#0A0E13'), borderWidth: 2 },
        },
        overallBest !== null
          ? {
              type: 'line',
              data: [],
              markLine: {
                symbol: 'none',
                lineStyle: { color: ok, type: 'dashed' },
                label: { formatter: `best ${overallBest.toFixed(1)}`, color: ok },
                data: [{ xAxis: overallBest }],
              },
            }
          : { type: 'line', data: [] },
      ],
      tooltip: { trigger: 'item' },
    }
  }, [rows, unit])

  return (
    <ReactECharts
      option={option}
      style={{ height: Math.max(rows.length * 56 + 40, 140) }}
      opts={{ renderer: 'svg' }}
      onEvents={
        onOutlierClick
          ? {
              click: (params: { seriesName?: string; data?: { t0: number; t1: number; section: string } }) => {
                if (params.seriesName === 'outliers' && params.data) {
                  onOutlierClick(params.data.section, params.data.t0, params.data.t1)
                }
              },
            }
          : undefined
      }
    />
  )
}
