// AnswerCard — comp S2-Workspace.dc.html aside. Answer / Evidence from data / Evidence from
// daily reports / Reasoning / Assumptions / Confidence, plus the 3 non-answer kinds.
import type { CopilotAnswer } from '../contracts/types'
import { ConfidenceBadge } from '../trust/ConfidenceBadge'
import { ClaimRow } from './ClaimRow'
import { DdrQuote } from './DdrQuote'

const SECTION_CLS = 'flex flex-col gap-1.5 border-t pt-2.5 first:border-t-0 first:pt-0'

function KindNotice({ title, body, color }: { title: string; body: string; color: string }) {
  return (
    <div
      className="flex flex-col gap-1 rounded border p-3"
      style={{ borderColor: color, background: `color-mix(in srgb, ${color} 10%, transparent)` }}
    >
      <span className="text-dense font-semibold" style={{ color }}>
        {title}
      </span>
      <p className="m-0 text-dense" style={{ color: 'var(--text)' }}>
        {body}
      </p>
    </div>
  )
}

export function AnswerCard({ answer }: { answer: CopilotAnswer }) {
  if (answer.kind === 'insufficient_data') {
    return (
      <KindNotice
        title="Insufficient data"
        body={answer.answer}
        color="var(--confidence-insufficient-fg)"
      />
    )
  }
  if (answer.kind === 'live_mode_required') {
    return <KindNotice title="Live mode required" body={answer.answer} color="var(--text-2)" />
  }
  if (answer.kind === 'out_of_scope') {
    return (
      <KindNotice
        title="Out of scope — advisory only"
        body={answer.answer}
        color="var(--confidence-medium-fg)"
      />
    )
  }

  const confidence = {
    level: answer.confidence,
    reason: answer.confidence_reason,
  } as const

  return (
    <div
      className="flex flex-col gap-2.5 rounded border p-3"
      style={{ borderColor: 'var(--line)', background: 'var(--panel-2)' }}
    >
      <div className={SECTION_CLS}>
        <span className="font-condensed text-label uppercase text-text-3">Answer</span>
        <p className="m-0 text-dense leading-relaxed" style={{ color: 'var(--text)' }}>
          {answer.answer}
        </p>
      </div>

      {answer.claims.length > 0 && (
        <div className={SECTION_CLS}>
          <span className="font-condensed text-label uppercase text-text-3">Evidence from data</span>
          {answer.claims.map((c, i) => (
            <ClaimRow key={i} claim={c} />
          ))}
          {answer.unverified_numbers_in_text && answer.unverified_numbers_in_text.length > 0 && (
            <div className="text-label" style={{ color: 'var(--danger)' }}>
              {'✕'} {answer.unverified_numbers_in_text.length} number
              {answer.unverified_numbers_in_text.length === 1 ? '' : 's'} failed the verifier — no
              matching tool output.
            </div>
          )}
        </div>
      )}

      {answer.ddr_quotes.length > 0 && (
        <div className={SECTION_CLS}>
          <span className="font-condensed text-label uppercase text-text-3">
            Evidence from daily reports
          </span>
          {answer.ddr_quotes.map((q, i) => (
            <DdrQuote key={i} quote={q} />
          ))}
        </div>
      )}

      {answer.reasoning && (
        <div className={SECTION_CLS}>
          <span className="font-condensed text-label uppercase text-text-3">Reasoning</span>
          <p className="m-0 text-dense leading-relaxed" style={{ color: 'var(--text-2)' }}>
            {answer.reasoning}
          </p>
        </div>
      )}

      {answer.assumptions.length > 0 && (
        <div className={SECTION_CLS}>
          <span className="font-condensed text-label uppercase text-text-3">Assumptions</span>
          <ul className="m-0 flex flex-col gap-1 pl-[18px] text-dense" style={{ color: 'var(--text-2)' }}>
            {answer.assumptions.map((a, i) => (
              <li key={i}>{a}</li>
            ))}
          </ul>
        </div>
      )}

      <div className={SECTION_CLS}>
        <span className="font-condensed text-label uppercase text-text-3">Confidence</span>
        <div className="flex flex-wrap items-center gap-2">
          <ConfidenceBadge c={confidence} />
        </div>
      </div>
    </div>
  )
}
