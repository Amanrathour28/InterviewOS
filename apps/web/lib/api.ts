const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1';

interface RequestOptions extends RequestInit {
  params?: Record<string, string>;
}

export class ApiError extends Error {
  status: number;
  data: any;

  constructor(message: string, status: number, data?: any) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
    this.data = data;
  }
}

let cachedToken: string | null = null;

export function setApiAuthToken(token: string | null) {
  cachedToken = token;
  if (typeof window !== 'undefined') {
    if (token) {
      localStorage.setItem('interviewos_token', token);
    } else {
      localStorage.removeItem('interviewos_token');
    }
  }
}

export function getApiAuthToken(): string | null {
  if (cachedToken) return cachedToken;
  if (typeof window !== 'undefined') {
    cachedToken = localStorage.getItem('interviewos_token');
  }
  return cachedToken;
}

export async function apiClient<T>(
  endpoint: string,
  options: RequestOptions = {}
): Promise<T> {
  const { params, headers: customHeaders, ...customOptions } = options;

  let url = `${API_BASE_URL}${endpoint.startsWith('/') ? endpoint : `/${endpoint}`}`;
  if (params) {
    const searchParams = new URLSearchParams(params);
    url += `?${searchParams.toString()}`;
  }

  const token = getApiAuthToken();
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    ...(customHeaders as Record<string, string>),
  };

  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }

  const response = await fetch(url, {
    ...customOptions,
    headers,
    credentials: 'include', // sends cookies for HTTP-only refresh tokens
  });

  if (!response.ok) {
    let errorData: any;
    try {
      errorData = await response.json();
    } catch {
      const fallbackDetail =
        response.statusText ||
        (response.status === 404
          ? 'API endpoint not found (HTTP 404)'
          : response.status === 502
          ? 'API server unavailable (HTTP 502)'
          : response.status === 503
          ? 'API service temporarily unavailable (HTTP 503)'
          : response.status === 504
          ? 'API gateway timeout (HTTP 504)'
          : `API request failed (HTTP ${response.status})`);
      errorData = { detail: fallbackDetail };
    }

    const message =
      errorData?.detail ||
      errorData?.message ||
      (response.status ? `API request failed (HTTP ${response.status})` : 'An unexpected error occurred');

    // Automatic token refresh handling on 401 if refresh token is available
    if (response.status === 401 && !endpoint.includes('/auth/login') && !endpoint.includes('/auth/refresh')) {
      const refreshed = await attemptTokenRefresh();
      if (refreshed) {
        return apiClient<T>(endpoint, options);
      }
    }

    throw new ApiError(message, response.status, errorData);
  }

  if (response.status === 204) {
    return {} as T;
  }

  return (await response.json()) as T;
}

let refreshPromise: Promise<boolean> | null = null;

async function attemptTokenRefresh(): Promise<boolean> {
  if (refreshPromise) {
    return refreshPromise;
  }

  refreshPromise = (async () => {
    try {
      const refreshRes = await fetch(`${API_BASE_URL}/auth/refresh`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
      });

      if (refreshRes.ok) {
        const data = await refreshRes.json();
        if (data?.access_token) {
          setApiAuthToken(data.access_token);
          return true;
        }
      }
    } catch {
      // refresh failed
    } finally {
      refreshPromise = null;
    }
    setApiAuthToken(null);
    return false;
  })();

  return refreshPromise;
}
