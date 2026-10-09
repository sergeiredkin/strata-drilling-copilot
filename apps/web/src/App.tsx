import { RouterProvider } from 'react-router-dom'
import { router } from './app/router'
import { KitPage } from './dev/KitPage'
import { TokensPage } from './dev/TokensPage'
import { TrackStackDebugPage } from './dev/TrackStackDebugPage'

export function App() {
  if (import.meta.env.DEV && window.location.pathname === '/dev/tokens') {
    return <TokensPage />
  }
  if (import.meta.env.DEV && window.location.pathname === '/dev/kit') {
    return <KitPage />
  }
  if (import.meta.env.DEV && window.location.pathname === '/dev/trackstack') {
    return <TrackStackDebugPage />
  }

  return <RouterProvider router={router} />
}
