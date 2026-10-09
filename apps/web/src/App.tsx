import { RouterProvider } from 'react-router-dom'
import { router } from './app/router'
import { KitPage } from './dev/KitPage'
import { TokensPage } from './dev/TokensPage'

export function App() {
  if (import.meta.env.DEV && window.location.pathname === '/dev/tokens') {
    return <TokensPage />
  }
  if (import.meta.env.DEV && window.location.pathname === '/dev/kit') {
    return <KitPage />
  }

  return <RouterProvider router={router} />
}
