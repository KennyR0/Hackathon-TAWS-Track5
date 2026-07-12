import { lazy, Suspense } from 'react'
import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom'
import { AppShell } from './layout/AppShell'
import { LoadingSkeleton } from '../shared/ui/primitives'

const SummaryPage = lazy(() => import('../features/summary/SummaryPage').then(module => ({ default: module.SummaryPage })))
const RadarPage = lazy(() => import('../features/radar/RadarPage').then(module => ({ default: module.RadarPage })))
const AssetDetailPage = lazy(() => import('../features/assets/AssetDetailPage').then(module => ({ default: module.AssetDetailPage })))
const SignalsPage = lazy(() => import('../features/signals/SignalsPage').then(module => ({ default: module.SignalsPage })))
const SignalDetailPage = lazy(() => import('../features/signals/SignalDetailPage').then(module => ({ default: module.SignalDetailPage })))
const BriefingsPage = lazy(() => import('../features/briefings/BriefingsPage').then(module => ({ default: module.BriefingsPage })))
const BriefingDetailPage = lazy(() => import('../features/briefings/BriefingDetailPage').then(module => ({ default: module.BriefingDetailPage })))
const ReviewsPage = lazy(() => import('../features/reviews/ReviewsPage').then(module => ({ default: module.ReviewsPage })))
const AuditPage = lazy(() => import('../features/audit/AuditPage').then(module => ({ default: module.AuditPage })))
const AuditDetailPage = lazy(() => import('../features/audit/AuditDetailPage').then(module => ({ default: module.AuditDetailPage })))
const AssistantPage = lazy(() => import('../features/assistant/AssistantPage').then(module => ({ default: module.AssistantPage })))

function RouteFallback() {
  return <LoadingSkeleton rows={10} />
}

export function AppRouter() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<AppShell />}>
          <Route index element={<Navigate replace to="/summary" />} />
          <Route
            path="summary"
            element={
              <Suspense fallback={<RouteFallback />}>
                <SummaryPage />
              </Suspense>
            }
          />
          <Route
            path="radar"
            element={
              <Suspense fallback={<RouteFallback />}>
                <RadarPage />
              </Suspense>
            }
          />
          <Route
            path="assets/:symbol"
            element={
              <Suspense fallback={<RouteFallback />}>
                <AssetDetailPage />
              </Suspense>
            }
          />
          <Route
            path="signals"
            element={
              <Suspense fallback={<RouteFallback />}>
                <SignalsPage />
              </Suspense>
            }
          />
          <Route
            path="signals/:signalId"
            element={
              <Suspense fallback={<RouteFallback />}>
                <SignalDetailPage />
              </Suspense>
            }
          />
          <Route
            path="briefings"
            element={
              <Suspense fallback={<RouteFallback />}>
                <BriefingsPage />
              </Suspense>
            }
          />
          <Route
            path="briefings/:briefingId"
            element={
              <Suspense fallback={<RouteFallback />}>
                <BriefingDetailPage />
              </Suspense>
            }
          />
          <Route
            path="reviews"
            element={
              <Suspense fallback={<RouteFallback />}>
                <ReviewsPage />
              </Suspense>
            }
          />
          <Route
            path="assistant"
            element={
              <Suspense fallback={<RouteFallback />}>
                <AssistantPage />
              </Suspense>
            }
          />
          <Route
            path="audit"
            element={
              <Suspense fallback={<RouteFallback />}>
                <AuditPage />
              </Suspense>
            }
          />
          <Route
            path="audit/:runId"
            element={
              <Suspense fallback={<RouteFallback />}>
                <AuditDetailPage />
              </Suspense>
            }
          />
          <Route path="*" element={<Navigate replace to="/summary" />} />
        </Route>
      </Routes>
    </BrowserRouter>
  )
}
