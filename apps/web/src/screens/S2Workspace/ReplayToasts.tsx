// T13.3 — up to 3 visible alert toasts (06 S8), each auto-dismissing after a few seconds.
import { useEffect } from 'react'
import type { Toast } from './useReplayToasts'

const AUTO_DISMISS_MS = 6000

function ReplayToast({ toast, onDismiss }: { toast: Toast; onDismiss: () => void }) {
  useEffect(() => {
    const timer = setTimeout(onDismiss, AUTO_DISMISS_MS)
    return () => clearTimeout(timer)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [toast.id])

  return (
    <div
      role="status"
      className="flex items-start gap-2 rounded border px-3 py-2 text-dense shadow-lg"
      style={{ borderColor: 'var(--danger)', background: 'var(--panel)', minWidth: 260 }}
    >
      <span className="flex-1">{toast.message}</span>
      <button type="button" onClick={onDismiss} aria-label="Dismiss alert" className="text-text-2 hover:text-text">
        ×
      </button>
    </div>
  )
}

export function ReplayToastList({
  toasts,
  onDismiss,
}: {
  toasts: Toast[]
  onDismiss: (id: string) => void
}) {
  if (toasts.length === 0) return null
  return (
    <div className="fixed right-4 top-20 z-50 flex flex-col gap-2">
      {toasts.map((t) => (
        <ReplayToast key={t.id} toast={t} onDismiss={() => onDismiss(t.id)} />
      ))}
    </div>
  )
}
