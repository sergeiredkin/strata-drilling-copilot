import { TokensPage } from './dev/TokensPage'

export function App() {
  if (import.meta.env.DEV && window.location.pathname === '/dev/tokens') {
    return <TokensPage />
  }

  return (
    <div data-theme="dark" className="min-h-screen bg-bg text-text">
      <p className="p-6">STRATA — scaffold (T0.1–T0.3). Shell arrives in T4.2.</p>
    </div>
  )
}
