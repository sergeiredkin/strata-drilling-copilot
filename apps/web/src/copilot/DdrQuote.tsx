// "Evidence from daily reports" quote — comp S2-Workspace.dc.html. Links to that well's
// Workspace; the DdrQuote contract carries well/date/ddr_activity_id, not a time window, so the
// link cannot be narrowed to the exact interval without fabricating one.
import type { DdrQuote as DdrQuoteT } from '../contracts/types'

export function DdrQuote({ quote }: { quote: DdrQuoteT }) {
  return (
    <blockquote
      className="m-0 border-l-2 pl-2.5 text-dense italic leading-snug"
      style={{ borderColor: 'var(--line)', color: 'var(--text)' }}
    >
      “{quote.text}”
      <a
        href={`/well/${quote.well}/workspace`}
        className="mt-1 block font-mono text-label not-italic"
        style={{ color: 'var(--text-2)' }}
      >
        {quote.well} · DDR {quote.date}
      </a>
    </blockquote>
  )
}
