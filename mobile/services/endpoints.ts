import api from './api';

export const authService = {
  login: (email: string, password: string) =>
    api.post('/auth/login', { email, password }),

  register: (data: { email: string; password: string; full_name: string; phone?: string }) =>
    api.post('/auth/register', data),
};

export const safetyScoreService = {
  getLocationScore: (lat: number, lng: number) =>
    api.get('/safety-score/location', { params: { lat, lng } }),

  getRouteScore: (origin: { lat: number; lng: number }, destination: { lat: number; lng: number }) =>
    api.post('/safety-score/route', { origin, destination }),

  getJourneyScore: (sessionId: string) =>
    api.get(`/safety-score/journey/${sessionId}`),
};

export const guardianService = {
  startSession: (userId: string) =>
    api.post('/guardian/start', { user_id: userId }),

  stopSession: (sessionId: string) =>
    api.post('/guardian/stop', { session_id: sessionId }),

  updateLocation: (sessionId: string, lat: number, lng: number) =>
    api.post('/guardian/update-location', { session_id: sessionId, lat, lng }),

  getSession: (sessionId: string) =>
    api.get(`/guardian/session/${sessionId}`),

  listActive: () =>
    api.get('/guardian/sessions/active'),

  getHistory: () =>
    api.get('/guardian/sessions/history'),

  acknowledgeSafety: (sessionId: string) =>
    api.post('/guardian/acknowledge-safety', { session_id: sessionId }),
};

export const guardianDashboardService = {
  getLovedOnes: () =>
    api.get('/guardian/dashboard/loved-ones'),

  getSessions: () =>
    api.get('/guardian/dashboard/sessions'),

  getAlerts: (limit?: number) =>
    api.get('/guardian/dashboard/alerts', { params: { limit } }),

  getHistory: (userId?: string) =>
    api.get('/guardian/dashboard/history', { params: { user_id: userId } }),

  requestCheck: (userId: string) =>
    api.post('/guardian/dashboard/request-check', { user_id: userId }),
};

export const safeRouteService = {
  generateRoutes: (startLat: number, startLng: number, endLat: number, endLng: number) =>
    api.post('/safe-route', { origin: { lat: startLat, lng: startLng }, destination: { lat: endLat, lng: endLng } }),
};

export const predictiveAlertService = {
  evaluate: (lat: number, lng: number, speed?: number, heading?: number) =>
    api.post('/predictive-alert', { location: { lat, lng }, speed }),

  evaluateWithAlternative: (lat: number, lng: number, speed?: number, heading?: number) =>
    api.post('/predictive-alert/with-alternative', { location: { lat, lng }, speed }),
};

export const nightGuardianService = {
  start: (userId: string, destinationLat: number, destinationLng: number) =>
    api.post('/operator/night-guardian/start', { user_id: userId, destination_lat: destinationLat, destination_lng: destinationLng }),

  stop: (userId: string) =>
    api.post('/operator/night-guardian/stop', { user_id: userId }),

  getStatus: (userId: string) =>
    api.get('/operator/night-guardian/status', { params: { user_id: userId } }),

  updateLocation: (userId: string, lat: number, lng: number) =>
    api.post('/operator/night-guardian/update-location', { user_id: userId, lat, lng }),
};

export const pushService = {
  registerToken: (token: string, deviceId: string) =>
    api.post('/push/token', { token, device_id: deviceId }),
};
