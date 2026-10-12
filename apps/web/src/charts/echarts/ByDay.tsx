// Lost hours by day — comp S3-Performance.dc.html. Bars for days with < 60% sensor coverage
// get a hatched pattern (ECharts decal) instead of the solid fill, per the comp's caption.
import ReactECharts from 'echarts-for-react'
import { useMemo } from 'react'

export type ByDayRow = { date: string; hours: number; coveragePct: number }

const LOW_COVERAGE_THRESHOLD = 60

function cssVar(name: string, fallback: string): string {
  if (typeof window === 'undefined') return fallback
  return getComputedStyle(document.documentElement).getPropertyValue(name).trim() || fallback
}

export function ByDay({ rows, onBarClick }: { rows: ByDayRow[]; onBarClick?: (date: string) => void }) {
  const option = useMemo(() => {
    const text2 = cssVar('--text-2', '#A9B6C3')
    const line = cssVar('--line', '#243040')
    const accent = cssVar('--accent', '#C77F17')
    const panel2 = cssVar('--panel-2', '#161D25')

    return {
      backgroundColor: 'transparent',
      grid: { left: 36, right: 16, top: 16, bottom: 28 },
      xAxis: {
        type: 'category',
        data: rows.map((r) => r.date.slice(5)),
        axisLine: { lineStyle: { color: text2 } },
        axisLabel: { color: text2, fontSize: 10 },
      },
      yAxis: {
        type: 'value',
        name: 'h',
        axisLine: { lineStyle: { color: text2 } },
        axisLabel: { color: text2 },
        splitLine: { lineStyle: { color: line } },
      },
      series: [
        {
          type: 'bar',
          data: rows.map((r) => ({
            value: r.hours,
            itemStyle: { color: accent },
            decal:
              r.coveragePct < LOW_COVERAGE_THRESHOLD
                ? { symbol: 'line', dashArrayX: [1, 0], dashArrayY: [4, 4], rotation: Math.PI / 4, color: panel2 }
                : undefined,
          })),
        },
      ],
      tooltip: {
        trigger: 'item',
        formatter: (p: { dataIndex: number }) => {
          const r = rows[p.dataIndex]
          if (!r) return ''
          return `${r.date}<br/>${r.hours.toFixed(1)} h · ${r.coveragePct.toFixed(0)}% coverage`
        },
      },
    }
  }, [rows])

  return (
    <ReactECharts
      option={option}
      style={{ height: 150 }}
      opts={{ renderer: 'svg' }}
      onEvents={
        onBarClick
          ? {
              click: (params: { dataIndex: number }) => {
                const row = rows[params.dataIndex]
                if (row) onBarClick(row.date)
              },
            }
          : undefined
      }
    />
  )
}
