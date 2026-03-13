// API Client with auth interceptors
import axios from 'axios';
import * as SecureStore from 'expo-secure-store';
import { Platform } from 'react-native';

const API_BASE = process.env.EXPO_PUBLIC_API_URL || 'https://Nagarik-showcase.preview.emergentagent.com';

const api = axios.create({
  baseURL: `${API_BASE}/api`,
  timeout: 15000,
  headers: { 'Content-Type': 'application/json' },
});

// Request interceptor — attach token
api.interceptors.request.use(async (config) => {
  let token: string | null = null;
  if (Platform.OS === 'web') {
    token = typeof localStorage !== 'undefined' ? localStorage.getItem('Nagarik_token') : null;
  } else {
    token = await SecureStore.getItemAsync('Nagarik_token');
  }
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// Response interceptor — handle 401
api.interceptors.response.use(
  (res) => res,
  async (error) => {
    if (error.response?.status === 401) {
      if (Platform.OS === 'web') {
        localStorage.removeItem('Nagarik_token');
      } else {
        await SecureStore.deleteItemAsync('Nagarik_token');
      }
    }
    return Promise.reject(error);
  },
);

export default api;
export { API_BASE };
