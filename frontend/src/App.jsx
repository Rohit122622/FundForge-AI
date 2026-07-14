import { BrowserRouter, Routes, Route } from 'react-router-dom';
import { Toaster } from 'react-hot-toast';


import PublicLayout from './layouts/PublicLayout';
import AuthLayout from './layouts/AuthLayout';
import DashboardLayout from './layouts/DashboardLayout';


import ProtectedRoute from './components/common/ProtectedRoute';
import ErrorBoundary from './components/common/ErrorBoundary';


import LandingPage from './pages/Landing/LandingPage';
import LoginPage from './pages/Login/LoginPage';
import RegisterPage from './pages/Register/RegisterPage';
import VerifyEmailPage from './pages/VerifyEmail/VerifyEmailPage';
import DashboardPage from './pages/Dashboard/DashboardPage';
import AnalyticsPage from './pages/Dashboard/AnalyticsPage';
import GrantFinderPage from './pages/GrantFinder/GrantFinderPage';
import GrantDetailsPage from './pages/GrantDetails/GrantDetailsPage';
import RecommendationsPage from './pages/GrantFinder/RecommendationsPage';
import EligibilityPage from './pages/GrantFinder/EligibilityPage';
import ProposalGeneratorPage from './pages/ProposalGenerator/ProposalGeneratorPage';
import StartupProfilePage from './pages/StartupProfile/StartupProfilePage';
import SavedGrantsPage from './pages/SavedGrants/SavedGrantsPage';
import DocumentsPage from './pages/SavedGrants/DocumentsPage';
import ApplicationTrackerPage from './pages/ApplicationTracker/ApplicationTrackerPage';
import SettingsPage from './pages/Settings/SettingsPage';
import NotFoundPage from './pages/NotFound/NotFoundPage';

export default function App() {
  return (
    <ErrorBoundary>
      <BrowserRouter>
        <Toaster position="top-right" toastOptions={{ className: '', duration: 4000 }} />

        <Routes>
          
          <Route element={<PublicLayout />}>
            <Route path="/" element={<LandingPage />} />
          </Route>

          {/* Auth pages */}
          <Route element={<AuthLayout />}>
            <Route path="/login" element={<LoginPage />} />
            <Route path="/register" element={<RegisterPage />} />
            <Route path="/verify-email" element={<VerifyEmailPage />} />
          </Route>

          {/* Protected dashboard pages */}
          <Route element={<ProtectedRoute><DashboardLayout /></ProtectedRoute>}>
            <Route path="/dashboard" element={<DashboardPage />} />
            <Route path="/grants" element={<GrantFinderPage />} />
            <Route path="/grants/recommendations" element={<RecommendationsPage />} />
            <Route path="/grants/:id" element={<GrantDetailsPage />} />
            <Route path="/eligibility" element={<EligibilityPage />} />
            <Route path="/proposals/generate" element={<ProposalGeneratorPage />} />
            <Route path="/profile" element={<StartupProfilePage />} />
            <Route path="/saved-grants" element={<SavedGrantsPage />} />
            <Route path="/documents" element={<DocumentsPage />} />
            <Route path="/tracker" element={<ApplicationTrackerPage />} />
            <Route path="/analytics" element={<AnalyticsPage />} />
            <Route path="/settings" element={<SettingsPage />} />
          </Route>

          {/* 404 */}
          <Route path="*" element={<NotFoundPage />} />
        </Routes>
      </BrowserRouter>
    </ErrorBoundary>
  );
}
