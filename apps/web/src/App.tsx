import { RouterProvider } from 'react-router-dom'
import { router } from './app/router'
import { TokensPage } from './dev/TokensPage'

export function App() {
  if (import.meta.env.DEV && window.location.pathname === '/dev/tokens') {
    return <TokensPage />
  }

  return <RouterProvider router={router} />
}
