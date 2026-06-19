import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom'
import { AddApartmentModal } from '@/components/apartments/AddApartmentModal'
import {
  ProtectedRoute,
  PublicOnlyRoute,
} from '@/components/auth/ProtectedRoute'
import { DashboardLayout } from '@/components/layout/DashboardLayout'
import { ToastContainer } from '@/components/ui/ToastContainer'
import { ApartmentsProvider } from '@/context/ApartmentsContext'
import { AuthProvider } from '@/context/AuthContext'
import { CommuteProvider } from '@/context/CommuteContext'
import { StudentProfileProvider } from '@/context/StudentProfileContext'
import { ToastProvider } from '@/context/ToastContext'
import { CalendarPage } from '@/pages/CalendarPage'
import { AnalyticsPage } from '@/pages/AnalyticsPage'
import { HuntingBoardPage } from '@/pages/HuntingBoardPage'
import { ListingDetailPage } from '@/pages/ListingDetailPage'
import { LoginPage } from '@/pages/LoginPage'
import { ProfilePage } from '@/pages/ProfilePage'
import { RegisterPage } from '@/pages/RegisterPage'

function AuthenticatedApp() {
  return (
    <StudentProfileProvider>
      <ApartmentsProvider>
        <CommuteProvider>
          <DashboardLayout />
          <AddApartmentModal />
        </CommuteProvider>
      </ApartmentsProvider>
    </StudentProfileProvider>
  )
}

export default function App() {
  return (
    <AuthProvider>
      <ToastProvider>
        <BrowserRouter>
          <Routes>
            <Route element={<PublicOnlyRoute />}>
              <Route path="/login" element={<LoginPage />} />
              <Route path="/register" element={<RegisterPage />} />
            </Route>

            <Route element={<ProtectedRoute />}>
              <Route element={<AuthenticatedApp />}>
                <Route index element={<HuntingBoardPage />} />
                <Route path="profile" element={<ProfilePage />} />
                <Route path="board/:id" element={<ListingDetailPage />} />
                <Route path="board" element={<Navigate to="/" replace />} />
                <Route path="calendar" element={<CalendarPage />} />
                <Route path="analytics" element={<AnalyticsPage />} />
                <Route path="settings" element={<Navigate to="/profile" replace />} />
              </Route>
            </Route>

            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
          <ToastContainer />
        </BrowserRouter>
      </ToastProvider>
    </AuthProvider>
  )
}
