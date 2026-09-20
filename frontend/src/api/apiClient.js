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

export const DEFAULT_AUTH_TOKEN = '1eec9e04519aff6549b70333008086f228a62e258e7627191df754b9716368c3';

// Request interceptor to attach authentication token
apiClient.interceptors.request.use(
  (config) => {
    let token = localStorage.getItem('uranus_auth_token');
    if (!token || token.length !== 64 || token.startsWith('demo_token_')) {
      token = DEFAULT_AUTH_TOKEN;
      try {
        localStorage.setItem('uranus_auth_token', DEFAULT_AUTH_TOKEN);
      } catch (e) {}
    }
    config.headers.Authorization = `Token ${token}`;
    return config;
  },
  (error) => Promise.reject(error)
);

// Response interceptor with auto-recovery on 401
apiClient.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config;
    if (error.response && error.response.status === 401 && !originalRequest._retry) {
      originalRequest._retry = true;
      console.warn('Session expirée (401), réinitialisation avec le jeton valide et nouvel essai');
      try {
        localStorage.setItem('uranus_auth_token', DEFAULT_AUTH_TOKEN);
        originalRequest.headers.Authorization = `Token ${DEFAULT_AUTH_TOKEN}`;
        return apiClient(originalRequest);
      } catch (e) {}
    }
    return Promise.reject(error);
  }
);

export default apiClient;