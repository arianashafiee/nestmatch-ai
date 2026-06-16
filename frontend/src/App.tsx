import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom'
import { AddApartmentModal } from '@/components/apartments/AddApartmentModal'
import { DashboardLayout } from '@/components/layout/DashboardLayout'
import { ToastContainer } from '@/components/ui/ToastContainer'
import { ApartmentsProvider } from '@/context/ApartmentsContext'
import { StudentProfileProvider } from '@/context/StudentProfileContext'
import { ToastProvider } from '@/context/ToastContext'
import { AnalyticsPage } from '@/pages/AnalyticsPage'
import { HomePage } from '@/pages/HomePage'
import { HuntingBoardPage } from '@/pages/HuntingBoardPage'
import { ListingDetailPage } from '@/pages/ListingDetailPage'
import { ProfilePage } from '@/pages/ProfilePage'
import { SettingsPage } from '@/pages/SettingsPage'

export default function App() {
  return (
    <ToastProvider>
      <StudentProfileProvider>
        <ApartmentsProvider>
          <BrowserRouter>
            <Routes>
              <Route element={<DashboardLayout />}>
                <Route index element={<HomePage />} />
                <Route path="profile" element={<ProfilePage />} />
                <Route path="board/:id" element={<ListingDetailPage />} />
                <Route path="board" element={<HuntingBoardPage />} />
                <Route path="analytics" element={<AnalyticsPage />} />
                <Route path="settings" element={<SettingsPage />} />
                <Route path="*" element={<Navigate to="/" replace />} />
              </Route>
            </Routes>
            <AddApartmentModal />
            <ToastContainer />
          </BrowserRouter>
        </ApartmentsProvider>
      </StudentProfileProvider>
    </ToastProvider>
  )
}
