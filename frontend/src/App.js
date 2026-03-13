import React from 'react';
import { BrowserRouter, Routes, Route, Navigate, useLocation } from 'react-router-dom';
import { Toaster } from 'sonner';
import { GoogleOAuthProvider } from '@react-oauth/google';
import { AuthProvider } from './contexts/AuthContext';
import ProtectedRoute from './components/ProtectedRoute';
import NagarikHomePage from './pages/NagarikHomePage';
import InvestorPage from './pages/InvestorPage';
import PilotSignupPage from './pages/PilotSignupPage';
import StatusPage from './pages/StatusPage';
import SafetyDashboard from './pages/SafetyDashboard';
import SystemStatusPage from './pages/SystemStatusPage';
import WhatsAppButton from './components/WhatsAppButton';
import NagarikChatbot from './components/NagarikChatbot';
import FamilyDashboard from './pages/FamilyDashboard';
import OperatorConsole from './pages/OperatorConsole';
import OperatorDashboard from './pages/OperatorDashboard';
import CaregiverDashboard from './pages/CaregiverDashboard';
import JourneyReplayPage from './pages/JourneyReplayPage';
import Login from './pages/Login';
import AdminPanel from './pages/AdminPanel';
import CommandCenterPage from './pages/CommandCenterPage';
import MobileLayout from './pages/mobile/MobileLayout';
import MobileHome from './pages/mobile/MobileHome';
import MobileSOS from './pages/mobile/MobileSOS';
import MobileFakeCall from './pages/mobile/MobileFakeCall';
import MobileSession from './pages/mobile/MobileSession';
import MobileLive from './pages/mobile/MobileLive';
import MobileSafeRoute from './pages/mobile/MobileSafeRoute';
import MobileAlerts from './pages/mobile/MobileAlerts';
import MobileProfile from './pages/mobile/MobileProfile';
import MobileGuardians from './pages/mobile/MobileGuardians';
import MobileAddGuardian from './pages/mobile/MobileAddGuardian';
import MobileContacts from './pages/mobile/MobileContacts';
import MobileAIInsights from './pages/mobile/MobileAIInsights';
import MobileNotifications from './pages/mobile/MobileNotifications';
import MobileNotificationSettings from './pages/mobile/MobileNotificationSettings';
import MobileGuardianLiveMap from './pages/mobile/MobileGuardianLiveMap';
import MobileIncidentReplay from './pages/mobile/MobileIncidentReplay';
import InviteLanding from './pages/mobile/InviteLanding';
import InstallPrompt from './components/mobile/InstallPrompt';
import './App.css';

// REMINDER: DO NOT HARDCODE THE URL, OR ADD ANY FALLBACKS OR REDIRECT URLS, THIS BREAKS THE AUTH
const GOOGLE_CLIENT_ID = process.env.REACT_APP_GOOGLE_CLIENT_ID;

const MARKETING_ROUTES = ['/', '/investors', '/pilot', '/telemetry', '/safety-dashboard', '/system-status'];

function MarketingWhatsApp() {
  const { pathname } = useLocation();
  if (!MARKETING_ROUTES.includes(pathname)) return null;
  return (
    <>
      <NagarikChatbot />
      <WhatsAppButton />
    </>
  );
}

function App() {
  const appContent = (
    <AuthProvider>
      <div className="App">
        <BrowserRouter>
          <Routes>
            <Route path="/" element={<NagarikHomePage />} />
            <Route path="/investors" element={<InvestorPage />} />
            <Route path="/pilot" element={<PilotSignupPage />} />
            <Route path="/telemetry" element={<StatusPage />} />
            <Route path="/safety-dashboard" element={<SafetyDashboard />} />
            <Route path="/system-status" element={<SystemStatusPage />} />
            <Route path="/login" element={<Login />} />
            <Route path="/invite/:token" element={<InviteLanding />} />
            <Route 
              path="/family/*" 
              element={
                <ProtectedRoute>
                  <FamilyDashboard />
                </ProtectedRoute>
              } 
            />
            <Route path="/operator/*" element={
              <ProtectedRoute>
                <OperatorConsole />
              </ProtectedRoute>
            } />
            <Route path="/admin/*" element={
              <ProtectedRoute>
                <AdminPanel />
              </ProtectedRoute>
            } />
            <Route path="/command-center" element={
              <ProtectedRoute>
                <CommandCenterPage />
              </ProtectedRoute>
            } />
            <Route path="/operator-dashboard" element={
              <ProtectedRoute>
                <OperatorDashboard />
              </ProtectedRoute>
            } />
            <Route path="/caregiver/*" element={
              <ProtectedRoute>
                <CaregiverDashboard />
              </ProtectedRoute>
            } />
            <Route path="/replay" element={
              <ProtectedRoute>
                <JourneyReplayPage />
              </ProtectedRoute>
            } />
            <Route path="/replay/:sessionId" element={
              <ProtectedRoute>
                <JourneyReplayPage />
              </ProtectedRoute>
            } />
            {/* Mobile PWA Routes */}
            <Route path="/m" element={
              <ProtectedRoute>
                <MobileLayout />
              </ProtectedRoute>
            }>
              <Route index element={<Navigate to="/m/home" replace />} />
              <Route path="home" element={<MobileHome />} />
              <Route path="sos" element={<MobileSOS />} />
              <Route path="fake-call" element={<MobileFakeCall />} />
              <Route path="session" element={<MobileSession />} />
              <Route path="live" element={<MobileLive />} />
              <Route path="safe-route" element={<MobileSafeRoute />} />
              <Route path="alerts" element={<MobileAlerts />} />
              <Route path="profile" element={<MobileProfile />} />
              <Route path="guardians" element={<MobileGuardians />} />
              <Route path="add-guardian" element={<MobileAddGuardian />} />
              <Route path="contacts" element={<MobileContacts />} />
              <Route path="ai" element={<MobileAIInsights />} />
              <Route path="notifications" element={<MobileNotifications />} />
              <Route path="notification-settings" element={<MobileNotificationSettings />} />
              <Route path="guardian-live-map" element={<MobileGuardianLiveMap />} />
              <Route path="incidents" element={<MobileIncidentReplay />} />
            </Route>
          </Routes>
          <MarketingWhatsApp />
          <InstallPrompt />
        </BrowserRouter>
        <Toaster position="top-right" richColors />
      </div>
    </AuthProvider>
  );

  // Wrap with GoogleOAuthProvider only if client ID is configured
  if (GOOGLE_CLIENT_ID) {
    return (
      <GoogleOAuthProvider clientId={GOOGLE_CLIENT_ID}>
        {appContent}
      </GoogleOAuthProvider>
    );
  }

  return appContent;
}

export default App;
