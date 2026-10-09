import { Outlet } from 'react-router-dom'
import { usePrefs } from '../state/prefs'
import { useViewUrlSync } from '../state/useViewUrlSync'
import { Nav } from './Nav'

export function Shell() {
  useViewUrlSync()
  const theme = usePrefs((s) => s.theme)

  return (
    <div className="min-h-screen bg-bg text-text" data-theme={theme}>
      <Nav />
      <Outlet />
    </div>
  )
}
