// Nav — docs/05_DESIGN_SYSTEM.md §6: 56px, brand "STRATA" condensed amber, links Field ·
// Workspace · Performance · Formation · Trust; right side ModeBadge, units toggle, Copilot
// toggle. ModeBadge is inlined here for now — T4.4 (trust kit) gives it its own component and
// this import switches over then.
import { NavLink } from 'react-router-dom'
import { isLiveMode } from '../data/createDataSource'
import { usePrefs } from '../state/prefs'

const LINKS = [
  { to: '/field', label: 'Field' },
  { to: '/well/15_9-F-11_A/workspace', label: 'Workspace' },
  { to: '/well/15_9-F-11_A/performance', label: 'Performance' },
  { to: '/well/15_9-F-11_A/formation', label: 'Formation' },
  { to: '/trust', label: 'Trust' },
]

function ModeBadgeInline() {
  const live = isLiveMode()
  return (
    <span
      className="rounded border px-2 py-0.5 text-label font-mono uppercase tracking-wide"
      style={{
        borderColor: 'var(--line)',
        color: live ? 'var(--ok)' : 'var(--mock-fg)',
        background: live ? 'transparent' : 'var(--mock-bg)',
      }}
    >
      {live ? 'Live' : 'Static mode'}
    </span>
  )
}

export function Nav() {
  const units = usePrefs((s) => s.units)
  const toggleUnits = usePrefs((s) => s.toggleUnits)

  return (
    <nav
      className="flex h-14 items-center justify-between border-b px-4"
      style={{ borderColor: 'var(--line)', background: 'var(--bg-nav)' }}
    >
      <div className="flex items-center gap-6">
        <span
          className="font-condensed text-dense font-semibold uppercase text-accent"
          style={{ letterSpacing: '.14em' }}
        >
          STRATA
        </span>
        <ul className="flex items-center gap-4">
          {LINKS.map((link) => (
            <li key={link.to}>
              <NavLink
                to={link.to}
                className={({ isActive }) =>
                  `text-dense ${isActive ? 'text-text' : 'text-text-2'} hover:text-text`
                }
              >
                {link.label}
              </NavLink>
            </li>
          ))}
        </ul>
      </div>
      <div className="flex items-center gap-3">
        <ModeBadgeInline />
        <button
          type="button"
          onClick={toggleUnits}
          className="min-h-9 rounded border px-3 text-dense text-text-2 hover:text-text"
          style={{ borderColor: 'var(--line)' }}
          aria-label="Toggle unit system"
        >
          {units === 'metric' ? 'Metric' : 'Oilfield'}
        </button>
        <button
          type="button"
          disabled
          className="min-h-9 rounded border px-3 text-dense text-text-3"
          style={{ borderColor: 'var(--line)' }}
          aria-label="Toggle copilot panel"
          title="Copilot dock arrives in T8.1"
        >
          Copilot
        </button>
      </div>
    </nav>
  )
}
