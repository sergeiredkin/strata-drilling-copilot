// Routes — docs/03_ARCHITECTURE.md §3.2. Screens not yet built (S6-S11) are placeholders; each
// lands in its own task (T5.1 S1 [done], T6.x S2 [done], T7.x S3 [done], T9.1 S5, T11+ S6/S7,
// T14 S9-S11).
import { createBrowserRouter, Navigate } from 'react-router-dom'
import { S1Field } from '../screens/S1Field/S1Field'
import { S2Workspace } from '../screens/S2Workspace/S2Workspace'
import { S3Performance } from '../screens/S3Performance/S3Performance'
import { S5Trust } from '../screens/S5Trust/S5Trust'
import { Placeholder } from './Placeholder'
import { Shell } from './Shell'

export const router = createBrowserRouter([
  {
    path: '/',
    element: <Shell />,
    children: [
      { index: true, element: <Navigate to="/field" replace /> },
      { path: 'field', element: <S1Field /> },
      { path: 'well/:id/workspace', element: <S2Workspace /> },
      { path: 'well/:id/performance', element: <S3Performance /> },
      { path: 'well/:id/formation', element: <Placeholder name="S6 Formation" /> },
      { path: 'well/:id/td', element: <Placeholder name="S9 Torque & drag" /> },
      { path: 'well/:id/mse', element: <Placeholder name="S10 MSE" /> },
      { path: 'well/:id/trips', element: <Placeholder name="S11 Trip-speed envelope" /> },
      { path: 'issues', element: <Placeholder name="S7 Issue catalogue" /> },
      { path: 'trust', element: <S5Trust /> },
      { path: '*', element: <Navigate to="/field" replace /> },
    ],
  },
])
