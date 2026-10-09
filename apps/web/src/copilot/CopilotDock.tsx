// Copilot dock — docs/06_SCREENS.md S4, comp inside S2-Workspace.dc.html. Mounted once in Shell
// (every screen); right panel >=1100px, bottom sheet below. T8.2 will have each screen publish a
// richer CopilotContext (mismatch "Ask copilot why", S6 "Generate formation brief" prefill) —
// here the context is derived from the route + the URL-synced view store, which already carries
// time/depth window and section.
import { useEffect, useRef, useState } from 'react'
import { useLocation } from 'react-router-dom'
import type { CopilotAnswer, CopilotContext, TraceStep, WellId } from '../contracts/types'
import { useSessions } from '../data/hooks'
import { getDataSource, isLiveMode } from '../data/createDataSource'
import { useView } from '../state/view'
import { AnswerCard } from './AnswerCard'
import { ContextLine } from './ContextLine'
import { Suggestions } from './Suggestions'
import { ToolTrace } from './ToolTrace'

function screenForPath(pathname: string): CopilotContext['screen'] {
  if (pathname.endsWith('/workspace')) return 'workspace'
  if (pathname.endsWith('/performance')) return 'performance'
  if (pathname.endsWith('/formation')) return 'formation'
  if (pathname.endsWith('/td')) return 'td'
  if (pathname.endsWith('/mse')) return 'mse'
  if (pathname.endsWith('/trips')) return 'trips'
  if (pathname.startsWith('/issues')) return 'issues'
  if (pathname.startsWith('/trust')) return 'trust'
  return 'field'
}

type Conversation =
  | { status: 'idle' }
  | { status: 'loading'; question: string; trace: TraceStep[] }
  | { status: 'done'; question: string; trace: TraceStep[]; answer: CopilotAnswer }
  | { status: 'error'; question: string; message: string }

function upsertStep(trace: TraceStep[], step: TraceStep): TraceStep[] {
  const next = trace.filter((s) => s.i !== step.i)
  next.push(step)
  next.sort((a, b) => a.i - b.i)
  return next
}

export function CopilotDock() {
  const location = useLocation()
  const panel = useView((s) => s.panel)
  const setPanel = useView((s) => s.setPanel)
  const sessionId = useView((s) => s.sessionId)
  const setSessionId = useView((s) => s.setSessionId)
  const timeRange = useView((s) => s.timeRange)
  const depthRange = useView((s) => s.depthRange)
  const section = useView((s) => s.section)

  const sessions = useSessions()
  const [conversation, setConversation] = useState<Conversation>({ status: 'idle' })
  const [input, setInput] = useState('')
  const autoAskedFor = useRef<string | null>(null)

  const wellMatch = location.pathname.match(/^\/well\/([^/]+)\//)
  const ctx: CopilotContext = {
    screen: screenForPath(location.pathname),
    well: wellMatch?.[1] as WellId | undefined,
    time_window: timeRange ?? undefined,
    depth_window: depthRange ?? undefined,
    section: section ?? undefined,
  }

  async function ask(question: string, askSessionId?: string) {
    setSessionId(askSessionId ?? null)
    setConversation({ status: 'loading', question, trace: [] })
    const ds = getDataSource()
    try {
      for await (const event of ds.ask(question, ctx, askSessionId)) {
        if (event.type === 'tool_call' || event.type === 'tool_result') {
          setConversation((prev) =>
            prev.status === 'loading'
              ? { ...prev, trace: upsertStep(prev.trace, event.step) }
              : prev,
          )
        } else if (event.type === 'answer') {
          setConversation((prev) =>
            prev.status === 'loading'
              ? { status: 'done', question, trace: prev.trace, answer: event.answer }
              : prev,
          )
        } else if (event.type === 'error') {
          setConversation({ status: 'error', question, message: event.message })
        }
      }
    } catch (err) {
      setConversation({ status: 'error', question, message: String(err) })
    }
  }

  useEffect(() => {
    if (!sessionId || !sessions.data || autoAskedFor.current === sessionId) return
    const match = sessions.data.sessions.find((s) => s.id === sessionId)
    if (match) {
      autoAskedFor.current = sessionId
      void ask(match.question, match.id)
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [sessionId, sessions.data])

  if (panel !== 'copilot') return null

  function submit() {
    const q = input.trim()
    if (!q) return
    setInput('')
    void ask(q)
  }

  return (
    <aside
      aria-label="Copilot"
      className="fixed inset-x-0 bottom-0 z-40 flex h-[70vh] flex-col gap-3 overflow-y-auto border-t p-4 [@media(min-width:1100px)]:inset-y-14 [@media(min-width:1100px)]:left-auto [@media(min-width:1100px)]:right-0 [@media(min-width:1100px)]:h-auto [@media(min-width:1100px)]:w-[400px] [@media(min-width:1100px)]:border-l [@media(min-width:1100px)]:border-t-0"
      style={{ background: 'var(--panel-2)', borderColor: 'var(--line)' }}
    >
      <div className="flex items-center justify-between gap-2">
        <span className="font-condensed text-card-title font-semibold">Copilot</span>
        <div className="flex items-center gap-2">
          <span
            className="rounded px-1.5 py-0.5 font-mono text-label"
            style={{ background: 'var(--mock-bg)', color: 'var(--mock-fg)' }}
          >
            {isLiveMode() ? 'live' : 'recorded session'}
          </span>
          <button
            type="button"
            onClick={() => setPanel(null)}
            aria-label="Close copilot panel"
            className="min-h-8 rounded border px-2 text-dense"
            style={{ borderColor: 'var(--line)' }}
          >
            ×
          </button>
        </div>
      </div>

      <ContextLine ctx={ctx} />

      {conversation.status !== 'idle' && (
        <>
          <div
            className="self-end max-w-[90%] rounded-md px-3 py-2.5 text-dense"
            style={{ background: 'var(--panel)' }}
          >
            {conversation.question}
          </div>
          {(conversation.status === 'loading' || conversation.status === 'done') &&
            conversation.trace.length > 0 && <ToolTrace steps={conversation.trace} />}
          {conversation.status === 'done' && <AnswerCard answer={conversation.answer} />}
          {conversation.status === 'error' && (
            <div className="text-dense" style={{ color: 'var(--danger)' }}>
              {conversation.message}
            </div>
          )}
          {conversation.status === 'loading' && (
            <div className="text-dense" style={{ color: 'var(--text-2)' }}>
              Thinking…
            </div>
          )}
        </>
      )}

      {sessions.data && (
        <Suggestions
          sessions={sessions.data}
          ctx={ctx}
          excludeId={conversation.status === 'done' ? sessionId ?? undefined : undefined}
          onPick={(id, question) => void ask(question, id)}
        />
      )}

      <div className="mt-auto flex gap-2">
        <label htmlFor="copilot-ask" className="sr-only">
          Ask the copilot
        </label>
        <input
          id="copilot-ask"
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === 'Enter') submit()
          }}
          placeholder={isLiveMode() ? 'Ask a question' : 'Live mode needed for free questions'}
          className="min-h-11 min-w-0 flex-1 rounded border px-3 text-dense"
          style={{ borderColor: 'var(--line)', background: 'var(--panel)', color: 'var(--text)' }}
        />
        <button
          type="button"
          onClick={submit}
          aria-label="Send"
          className="min-h-11 rounded border px-3 text-dense"
          style={{ borderColor: 'var(--line)', background: 'var(--panel)' }}
        >
          Ask
        </button>
      </div>
    </aside>
  )
}
