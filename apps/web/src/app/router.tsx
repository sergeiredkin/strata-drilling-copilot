// Routes — docs/03_ARCHITECTURE.md §3.2. Screens not yet built (S2-S11) are placeholders; each
// lands in its own task (T5.1 S1, T6.x S2, T7.x S3, T9.1 S5, T11+ S6/S7, T14 S9-S11).
import { createBrowserRouter, Navigate } from 'react-router-dom'
import { Placeholder } from './Placeholder'
import { Shell } from './Shell'

export const router = createBrowserRouter([
  {
    path: '/',
    element: <Shell />,
    children: [
      { index: true, element: <Navigate to="/field" replace /> },
      { path: 'field', element: <Placeholder name="S1 Field overview" /> },
      { path: 'well/:id/workspace', element: <Placeholder name="S2 Well workspace" /> },
      { path: 'well/:id/performance', element: <Placeholder name="S3 Performance" /> },
      { path: 'well/:id/formation', element: <Placeholder name="S6 Formation" /> },
      { path: 'well/:id/td', element: <Placeholder name="S9 Torque & drag" /> },
      { path: 'well/:id/mse', element: <Placeholder name="S10 MSE" /> },
      { path: 'well/:id/trips', element: <Placeholder name="S11 Trip-speed envelope" /> },
      { path: 'issues', element: <Placeholder name="S7 Issue catalogue" /> },
      { path: 'trust', element: <Placeholder name="S5 Trust" /> },
      { path: '*', element: <Navigate to="/field" replace /> },
    ],
  },
])
