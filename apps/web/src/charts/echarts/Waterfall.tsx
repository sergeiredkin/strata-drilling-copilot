// Lost-time waterfall (categories -> total), comp S3-Performance.dc.html — stacked bar with an
// invisible "base" series to fake waterfall offsets, the standard ECharts waterfall pattern.
import ReactECharts from 'echarts-for-react'
import { useMemo } from 'react'

export type WaterfallItem = { name: string; hours: number; color: string }

function cssVar(name: string, fallback: string): string {
  if (typeof window === 'undefined') return fallback
  return getComputedStyle(document.documentElement).getPropertyValue(name).trim() || fallback
}

export function Waterfall({ items, total }: { items: WaterfallItem[]; total: number }) {
  const option = useMemo(() => {
    const text2 = cssVar('--text-2', '#A9B6C3')
    const text = cssVar('--text', '#DCE3EA')
    const line = cssVar('--line', '#243040')
    const accent = cssVar('--accent', '#F5A524')

    const names = [...items.map((i) => i.name), 'Total']
    let acc = 0
    const bases = items.map((i) => {
      const b = acc
      acc += i.hours
      return b
    })
    bases.push(0)
    const values = [...items.map((i) => i.hours), total]
    const colors = [...items.map((i) => i.color), accent]

    return {
      backgroundColor: 'transparent',
      grid: { left: 36, right: 16, top: 24, bottom: 48 },
      xAxis: {
        type: 'category',
        data: names,
        axisLine: { lineStyle: { color: text2 } },
        axisLabel: { color: text2, fontSize: 11, width: 70, overflow: 'break', interval: 0 },
      },
      yAxis: {
        type: 'value',
        name: 'hours',
        axisLine: { lineStyle: { color: text2 } },
        axisLabel: { color: text2 },
        splitLine: { lineStyle: { color: line } },
      },
      series: [
        { type: 'bar', stack: 'wf', data: bases, itemStyle: { color: 'transparent' }, silent: true },
        {
          type: 'bar',
          stack: 'wf',
          data: values.map((v, i) => ({ value: v, itemStyle: { color: colors[i] } })),
          label: { show: true, position: 'top', color: text, formatter: (p: { value: number }) => p.value.toFixed(1) },
        },
      ],
      tooltip: { trigger: 'axis', axisPointer: { type: 'none' } },
    }
  }, [items, total])

  return <ReactECharts option={option} style={{ height: 240 }} />
}
