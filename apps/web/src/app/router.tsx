// Routes — docs/03_ARCHITECTURE.md §3.2. Screens not yet built (S6-S11) are placeholders; each
// lands in its own task (T5.1 S1 [done], T6.x S2 [done], T7.x S3 [done], T9.1 S5, T11+ S6/S7,
// T14 S9-S11).
//
// S3/S5 (the only screens that pull in ECharts) are lazy — docs/08_TESTING_AND_ACCEPTANCE.md §4:
// "JS bundle ≤ 450 kB gzip for initial route (lazy-load ECharts and S6+)". S1/S2 (uPlot only,
// the screens on the P0 demo path that must render fast) stay eager.
import { lazy, Suspense } from 'react'
import { createBrowserRouter, Navigate } from 'react-router-dom'
import { S1Field } from '../screens/S1Field/S1Field'
import { S2Workspace } from '../screens/S2Workspace/S2Workspace'
import { Placeholder } from './Placeholder'
import { Shell } from './Shell'

const S3Performance = lazy(() =>
  import('../screens/S3Performance/S3Performance').then((m) => ({ default: m.S3Performance })),
)
const S5Trust = lazy(() => import('../screens/S5Trust/S5Trust').then((m) => ({ default: m.S5Trust })))
const S6Formation = lazy(() => import('../screens/S6Formation/S6Formation').then((m) => ({ default: m.S6Formation })))
const S7Issues = lazy(() => import('../screens/S7Issues/S7Issues').then((m) => ({ default: m.S7Issues })))

const LAZY_FALLBACK = <div className="p-6 text-text-2">Loading…</div>

export const router = createBrowserRouter([
  {
    path: '/',
    element: <Shell />,
    children: [
      { index: true, element: <Navigate to="/field" replace /> },
      { path: 'field', element: <S1Field /> },
      { path: 'well/:id/workspace', element: <S2Workspace /> },
      {
        path: 'well/:id/performance',
        element: (
          <Suspense fallback={LAZY_FALLBACK}>
            <S3Performance />
          </Suspense>
        ),
      },
      {
        path: 'well/:id/formation',
        element: (
          <Suspense fallback={LAZY_FALLBACK}>
            <S6Formation />
          </Suspense>
        ),
      },
      { path: 'well/:id/td', element: <Placeholder name="S9 Torque & drag" /> },
      { path: 'well/:id/mse', element: <Placeholder name="S10 MSE" /> },
      { path: 'well/:id/trips', element: <Placeholder name="S11 Trip-speed envelope" /> },
      {
        path: 'issues',
        element: (
          <Suspense fallback={LAZY_FALLBACK}>
            <S7Issues />
          </Suspense>
        ),
      },
      {
        path: 'trust',
        element: (
          <Suspense fallback={LAZY_FALLBACK}>
            <S5Trust />
          </Suspense>
        ),
      },
      { path: '*', element: <Navigate to="/field" replace /> },
    ],
  },
], { basename: import.meta.env.BASE_URL })
