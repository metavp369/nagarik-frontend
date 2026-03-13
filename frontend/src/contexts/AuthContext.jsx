// Auth Context for managing user state — Dual-mode: Local JWT + Cognito
import React, { createContext, useContext, useState, useEffect, useCallback, useRef } from 'react';
import { setToken, getToken, isAuthenticated as checkAuth } from '../api';
import { jwtDecode } from 'jwt-decode';
import api from '../api';

const AuthContext = createContext(null);

export const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);
  const [authProvider, setAuthProvider] = useState('local');
  const refreshTimerRef = useRef(null);

  // Initialize from stored token
  useEffect(() => {
    const token = getToken();
    if (token) {
      try {
        const decoded = jwtDecode(token);
        if (decoded.exp * 1000 > Date.now()) {
          const groups = decoded['cognito:groups'] || [];
          setUser({
            id: decoded.sub,
            role: decoded.role || 'guardian',
            roles: groups.length > 0 ? groups : [decoded.role || 'guardian'],
            email: decoded.email || null,
            full_name: decoded.full_name || null,
          });
          const provider = localStorage.getItem('Nagarik_auth_provider') || 'local';
          setAuthProvider(provider);

          // Schedule token refresh if Cognito
          if (provider === 'cognito') {
            scheduleRefresh(decoded.exp);
          }
        } else {
          setToken(null);
        }
      } catch {
        setToken(null);
      }
    }
    setLoading(false);
  }, []);

  const scheduleRefresh = useCallback((expTimestamp) => {
    if (refreshTimerRef.current) clearTimeout(refreshTimerRef.current);

    const msUntilExpiry = expTimestamp * 1000 - Date.now();
    // Refresh 2 minutes before expiry
    const refreshIn = Math.max(msUntilExpiry - 120000, 10000);

    refreshTimerRef.current = setTimeout(async () => {
      const refreshToken = localStorage.getItem('Nagarik_refresh_token');
      const email = localStorage.getItem('Nagarik_email');
      const cognitoUsername = localStorage.getItem('Nagarik_cognito_username');
      if (!refreshToken) return;

      try {
        const resp = await api.post('/auth/refresh', {
          refresh_token: refreshToken,
          email: email || '',
          cognito_username: cognitoUsername || '',
        });
        if (resp.data?.access_token) {
          setToken(resp.data.access_token);
          const decoded = jwtDecode(resp.data.access_token);
          const groups = decoded['cognito:groups'] || [];
          setUser({
            id: decoded.sub,
            role: decoded.role || 'guardian',
            roles: groups.length > 0 ? groups : [decoded.role || 'guardian'],
            email: decoded.email || null,
            full_name: decoded.full_name || null,
          });
          scheduleRefresh(decoded.exp);
        }
      } catch {
        // Refresh failed — user must re-login
        logout();
      }
    }, refreshIn);
  }, []);

  const login = useCallback((token, extra = {}) => {
    setToken(token);
    const decoded = jwtDecode(token);
    const groups = decoded['cognito:groups'] || [];
    setUser({
      id: decoded.sub,
      role: decoded.role || 'guardian',
      roles: groups.length > 0 ? groups : [decoded.role || 'guardian'],
      email: decoded.email || null,
      full_name: decoded.full_name || null,
    });

    const provider = extra.auth_provider || 'local';
    setAuthProvider(provider);
    localStorage.setItem('Nagarik_auth_provider', provider);

    if (extra.refresh_token) {
      localStorage.setItem('Nagarik_refresh_token', extra.refresh_token);
    }
    if (extra.cognito_username) {
      localStorage.setItem('Nagarik_cognito_username', extra.cognito_username);
    }
    if (decoded.email) {
      localStorage.setItem('Nagarik_email', decoded.email);
    }

    if (provider === 'cognito') {
      scheduleRefresh(decoded.exp);
    }
  }, [scheduleRefresh]);

  const logout = useCallback(() => {
    if (refreshTimerRef.current) clearTimeout(refreshTimerRef.current);
    setToken(null);
    setUser(null);
    setAuthProvider('local');
    localStorage.removeItem('Nagarik_auth_provider');
    localStorage.removeItem('Nagarik_refresh_token');
    localStorage.removeItem('Nagarik_cognito_username');
    localStorage.removeItem('Nagarik_email');
  }, []);

  const isAuthenticated = useCallback(() => !!user && checkAuth(), [user]);

  return (
    <AuthContext.Provider value={{ user, login, logout, isAuthenticated, loading, authProvider }}>
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};
