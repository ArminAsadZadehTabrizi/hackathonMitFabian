import type { AxiosRequestConfig } from 'axios';

import axios from 'axios';

import { CONFIG } from 'src/global-config';

// ----------------------------------------------------------------------

// Fallback für baseURL wenn nicht gesetzt
const getBaseURL = () => {
  // Immer Backend-URL verwenden (auch beim SSR)
  if (CONFIG.serverUrl) {
    return CONFIG.serverUrl;
  }
  // Fallback für Development
  return 'http://localhost:8000';
};

const axiosInstance = axios.create({
  baseURL: getBaseURL(),
  headers: {
    'Content-Type': 'application/json',
  },
});

// Debug: Zeige baseURL beim Start
if (typeof window !== 'undefined') {
  console.log('🔗 Axios baseURL:', getBaseURL() || 'NICHT GESETZT - API Calls werden fehlschlagen!');
}

/**
 * Optional: Add token (if using auth)
 *
 axiosInstance.interceptors.request.use((config) => {
  const token = localStorage.getItem('accessToken');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});
*
*/

axiosInstance.interceptors.response.use(
  (response) => response,
  (error) => {
    const statusCode = error?.response?.status;
    const message = error?.response?.data?.message || error?.message || 'Something went wrong!';
    const url = error?.config?.url || error?.request?.url || 'unknown';
    
    // Debug: Zeige mehr Details bei 404
    if (statusCode === 404) {
      console.warn(`⚠️  API Endpoint nicht gefunden (404): ${url}`);
      console.warn(`   BaseURL: ${CONFIG.serverUrl || 'NICHT GESETZT!'}`);
      console.warn(`   Vollständige URL: ${CONFIG.serverUrl}${url}`);
    } else {
      console.error('Axios error:', message);
    }
    
    return Promise.reject(new Error(message));
  }
);

export default axiosInstance;

// ----------------------------------------------------------------------

export const fetcher = async <T = unknown>(
  args: string | [string, AxiosRequestConfig]
): Promise<T> => {
  try {
    const [url, config] = Array.isArray(args) ? args : [args, {}];
    
    // Bestimme Backend-URL (immer gesetzt, auch beim SSR)
    const backendUrl = process.env.NEXT_PUBLIC_SERVER_URL || 'http://localhost:8000';
    const fullUrl = url.startsWith('http') ? url : `${backendUrl}${url}`;
    
    // Server-Side (SSR) oder Client-Side: Nutze fetch direkt
    // Das funktioniert sowohl im Browser als auch beim SSR
    if (typeof window === 'undefined') {
      console.log(`🔗 SSR Request: ${fullUrl}`);
    } else {
      console.log(`🔗 Client Request: ${fullUrl}`);
    }
    
    const response = await fetch(fullUrl, {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
      },
      ...config,
      cache: 'no-store',
    });
    
    if (!response.ok) {
      const errorText = await response.text();
      console.error(`❌ API Error: ${response.status} - ${errorText}`);
      throw new Error(`HTTP ${response.status}: ${response.statusText}`);
    }
    
    return await response.json();
  } catch (error: any) {
    const statusCode = error?.status || error?.response?.status;
    const requestUrl = error?.url || error?.config?.url || 'unknown';
    const backendUrl = process.env.NEXT_PUBLIC_SERVER_URL || 'http://localhost:8000';
    const fullUrl = requestUrl.startsWith('http') ? requestUrl : `${backendUrl}${requestUrl}`;
    
    // Zeige detaillierte Fehler-Info
    if (statusCode === 404 || error?.message?.includes('404')) {
      console.error(`❌ 404 Error: Endpoint nicht gefunden`);
      console.error(`   Requested URL: ${requestUrl}`);
      console.error(`   Backend URL: ${backendUrl}`);
      console.error(`   Full URL: ${fullUrl}`);
      console.error(`   Backend läuft? Prüfe: curl ${fullUrl}`);
    } else {
      console.error('Fetcher failed:', error);
    }
    throw error;
  }
};

// ----------------------------------------------------------------------

export const endpoints = {
  chat: '/api/chat',
  kanban: '/api/kanban',
  calendar: '/api/calendar',
  auth: {
    me: '/api/auth/me',
    signIn: '/api/auth/sign-in',
    signUp: '/api/auth/sign-up',
  },
  mail: {
    list: '/api/mail/list',
    details: '/api/mail/details',
    labels: '/api/mail/labels',
  },
  post: {
    list: '/api/post/list',
    details: '/api/post/details',
    latest: '/api/post/latest',
    search: '/api/post/search',
  },
  product: {
    list: '/api/product/list',
    details: '/api/product/details',
    search: '/api/product/search',
  },
  receipts: '/api/receipts',
  analytics: {
    summary: '/api/analytics/summary',
    monthly: '/api/analytics/monthly',
    category: '/api/analytics/category',
    vendors: '/api/analytics/vendors',
  },
  audit: '/api/audit',
  chatQuery: '/api/chat/query',
} as const;
