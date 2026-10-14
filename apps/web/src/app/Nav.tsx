// Nav — docs/05_DESIGN_SYSTEM.md §6: 56px, brand "STRATA" condensed amber, links Field ·
// Workspace · Performance · Formation · Issues · Trust; right side ModeBadge, units toggle,
// Copilot toggle.
import { NavLink } from 'react-router-dom'
import { usePrefs } from '../state/prefs'
import { useView } from '../state/view'
import { ModeBadge } from '../trust/ModeBadge'

const LINKS = [
  { to: '/field', label: 'Field' },
  { to: '/well/15_9-F-11_A/workspace', label: 'Workspace' },
  { to: '/well/15_9-F-11_A/performance', label: 'Performance' },
  { to: '/well/15_9-F-11_A/formation', label: 'Formation' },
  { to: '/issues', label: 'Issues' },
  { to: '/trust', label: 'Trust' },
]

export function Nav() {
  const units = usePrefs((s) => s.units)
  const toggleUnits = usePrefs((s) => s.toggleUnits)
  const panel = useView((s) => s.panel)
  const setPanel = useView((s) => s.setPanel)

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
        <ModeBadge />
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
          onClick={() => setPanel(panel === 'copilot' ? null : 'copilot')}
          aria-pressed={panel === 'copilot'}
          className="min-h-9 rounded border px-3 text-dense"
          style={{
            borderColor: panel === 'copilot' ? 'var(--accent)' : 'var(--line)',
            color: panel === 'copilot' ? 'var(--text)' : 'var(--text-2)',
          }}
          aria-label="Toggle copilot panel"
        >
          Copilot {panel === 'copilot' ? '●' : ''}
        </button>
      </div>
    </nav>
  )
}
