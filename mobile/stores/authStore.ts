// Auth Store using Zustand
import { create } from 'zustand';
import * as SecureStore from 'expo-secure-store';
import { Platform } from 'react-native';
import { authService } from '../services/endpoints';

type ProfileMode = 'women' | 'kids' | 'parents';

interface User {
  id: string;
  email: string;
  role: string;
  full_name: string;
}

interface AuthState {
  token: string | null;
  user: User | null;
  profileMode: ProfileMode;
  isLoading: boolean;
  isReady: boolean;

  setProfileMode: (mode: ProfileMode) => void;
  login: (email: string, password: string) => Promise<void>;
  register: (data: { email: string; password: string; full_name: string; phone?: string }) => Promise<void>;
  logout: () => Promise<void>;
  loadToken: () => Promise<void>;
}

const saveToken = async (token: string) => {
  if (Platform.OS === 'web') {
    localStorage.setItem('Nagarik_token', token);
  } else {
    await SecureStore.setItemAsync('Nagarik_token', token);
  }
};

const removeToken = async () => {
  if (Platform.OS === 'web') {
    localStorage.removeItem('Nagarik_token');
  } else {
    await SecureStore.deleteItemAsync('Nagarik_token');
  }
};

const loadStoredToken = async (): Promise<string | null> => {
  if (Platform.OS === 'web') {
    return typeof localStorage !== 'undefined' ? localStorage.getItem('Nagarik_token') : null;
  }
  return SecureStore.getItemAsync('Nagarik_token');
};

const parseJwt = (token: string): User | null => {
  try {
    const base64 = token.split('.')[1].replace(/-/g, '+').replace(/_/g, '/');
    const payload = JSON.parse(
      Platform.OS === 'web'
        ? atob(base64)
        : Buffer.from
          ? Buffer.from(base64, 'base64').toString('utf8')
          : atob(base64),
    );
    return {
      id: payload.sub,
      email: payload.email,
      role: payload.role,
      full_name: payload.full_name,
    };
  } catch {
    return null;
  }
};

const saveProfileMode = async (mode: ProfileMode) => {
  if (Platform.OS === 'web') {
    localStorage.setItem('Nagarik_profile', mode);
  } else {
    await SecureStore.setItemAsync('Nagarik_profile', mode);
  }
};

const loadProfileMode = async (): Promise<ProfileMode> => {
  let stored: string | null = null;
  if (Platform.OS === 'web') {
    stored = typeof localStorage !== 'undefined' ? localStorage.getItem('Nagarik_profile') : null;
  } else {
    stored = await SecureStore.getItemAsync('Nagarik_profile');
  }
  return (stored as ProfileMode) || 'women';
};

export const useAuthStore = create<AuthState>((set) => ({
  token: null,
  user: null,
  profileMode: 'women',
  isLoading: false,
  isReady: false,

  setProfileMode: async (mode: ProfileMode) => {
    await saveProfileMode(mode);
    set({ profileMode: mode });
  },

  login: async (email, password) => {
    set({ isLoading: true });
    try {
      const res = await authService.login(email, password);
      const { access_token } = res.data;
      await saveToken(access_token);
      const user = parseJwt(access_token);
      const profileMode = await loadProfileMode();
      set({ token: access_token, user, profileMode, isLoading: false });
    } catch (e) {
      set({ isLoading: false });
      throw e;
    }
  },

  register: async (data) => {
    set({ isLoading: true });
    try {
      const res = await authService.register(data);
      const { access_token } = res.data;
      await saveToken(access_token);
      const user = parseJwt(access_token);
      set({ token: access_token, user, isLoading: false });
    } catch (e) {
      set({ isLoading: false });
      throw e;
    }
  },

  logout: async () => {
    await removeToken();
    set({ token: null, user: null, isReady: true });
  },

  loadToken: async () => {
    const token = await loadStoredToken();
    if (token) {
      const user = parseJwt(token);
      const profileMode = await loadProfileMode();
      set({ token, user, profileMode, isReady: true });
    } else {
      set({ isReady: true });
    }
  },
}));
