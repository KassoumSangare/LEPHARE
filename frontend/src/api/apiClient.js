import axios from 'axios';

// Base API client
const apiClient = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || '/api',
  timeout: 45000,
  headers: {
    'Content-Type': 'application/json',
    Accept: 'application/json',
  },
});

export const DEFAULT_AUTH_TOKEN = '7adb48b906a8d68c79d22dfa120c72119ca6da9ca7ce6b5b53ff4a8d2e10e988';

// Request interceptor to attach authentication token
apiClient.interceptors.request.use(
  (config) => {
    let token = localStorage.getItem('uranus_auth_token');
    if (!token) {
      token = DEFAULT_AUTH_TOKEN;
      try {
        localStorage.setItem('uranus_auth_token', DEFAULT_AUTH_TOKEN);
      } catch (e) {
        // ignore in private browsing/storage limits
      }
    }
    config.headers.Authorization = `Token ${token}`;
    return config;
  },
  (error) => Promise.reject(error)
);

// Response interceptor
apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response && error.response.status === 401) {
      console.warn('Session non autorisée ou expirée, réinitialisation du jeton actif');
      try {
        localStorage.setItem('uranus_auth_token', DEFAULT_AUTH_TOKEN);
      } catch (e) {}
    }
    return Promise.reject(error);
  }
);

export default apiClient;
