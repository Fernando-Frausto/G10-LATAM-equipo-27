import { lazy, Suspense } from 'react'
import {
  BrowserRouter,
  Navigate,
  Route,
  Routes,
} from 'react-router-dom'

import MainLayout from './layouts/MainLayout'
import ProtectedRoute from './components/ProtectedRoute'
import RoleProtectedRoute from './components/RoleProtectedRoute'
import LazyRouteErrorBoundary from './components/LazyRouteErrorBoundary'
import RouteLoadingFallback from './components/RouteLoadingFallback'

// Importaciones diferidas (React.lazy) para code-splitting por rutas
const Dashboard = lazy(() => import('./pages/Dashboard'))
const Messages = lazy(() => import('./pages/Messages'))
const Highlights = lazy(() => import('./pages/Highlights'))
const Analytics = lazy(() => import('./pages/Analytics'))
const ContentStudio = lazy(() => import('./pages/ContentStudio'))
const Audit = lazy(() => import('./pages/Audit'))
const Security = lazy(() => import('./pages/Security'))
const Settings = lazy(() => import('./pages/Settings'))
const Login = lazy(() => import('./pages/Login'))
const Hashtags = lazy(() => import('./pages/Hashtags'))
const Audience = lazy(() => import('./pages/Audience'))
const Calendar = lazy(() => import('./pages/Calendar'))
const Export = lazy(() => import('./pages/Export'))
const MyReports = lazy(() => import('./pages/MyReports'))
const OCIStorage = lazy(() => import('./pages/OCIStorage'))

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route
          path="/login"
          element={
            <LazyRouteErrorBoundary>
              <Suspense fallback={<RouteLoadingFallback />}>
                <Login />
              </Suspense>
            </LazyRouteErrorBoundary>
          }
        />

        <Route
          element={
            <ProtectedRoute />
          }
        >
          <Route element={<MainLayout />}>
          <Route path="/" element={<Navigate to="/dashboard" replace />} />
          <Route path="/dashboard" element={<Dashboard />} />
          <Route path="/messages" element={<Messages />} />

          <Route
            element={
              <RoleProtectedRoute
                allowedRoles={["admin", "reviewer"]}
              />
            }
          >
            <Route path="/highlights" element={<Highlights />} />
            <Route path="/hashtags" element={<Hashtags />} />
            <Route path="/audience" element={<Audience />} />
            <Route path="/calendar" element={<Calendar />} />
            <Route path="/export" element={<Export />} />
            <Route path="/my-reports" element={<MyReports />} />
          </Route>

          <Route
            element={
              <RoleProtectedRoute
                allowedRoles={["admin", "reviewer", "community_manager"]}
              />
            }
          >
            <Route path="/analytics" element={<Analytics />} />
            <Route path="/content" element={<ContentStudio />} />
            <Route path="/approvals" element={<Navigate to="/content" replace />} />
            <Route path="/oci-storage" element={<OCIStorage />} />
          </Route>

          <Route
            element={<RoleProtectedRoute allowedRoles={["admin"]} />}
          >
            <Route path="/audit" element={<Audit />} />
            <Route path="/security" element={<Security />} />
            <Route path="/settings" element={<Settings />} />
          </Route>

          <Route
            path="*"
            element={<Navigate to="/dashboard" replace />}
          />
          </Route>
        </Route>
      </Routes>
    </BrowserRouter>
  )
}

export default App
