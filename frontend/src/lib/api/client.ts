// 저수준 HTTP 클라이언트 — base URL · JSON · Bearer 토큰 · 타임아웃 · 401 refresh 재시도.
import { API_BASE } from './config';

const TOKEN_KEY = 'tamaya-auth-token';
const REFRESH_KEY = 'tamaya-refresh-token';

export const getToken = (): string | null => {
  try {
    return localStorage.getItem(TOKEN_KEY);
  } catch {
    return null;
  }
};

const getRefreshToken = (): string | null => {
  try {
    return localStorage.getItem(REFRESH_KEY);
  } catch {
    return null;
  }
};

export const setToken = (t: string): void => {
  try {
    localStorage.setItem(TOKEN_KEY, t);
    window.dispatchEvent(new Event('tamaya-auth-changed'));
  } catch {
    // ignore quota/unavailable
  }
};

/** access + refresh 쌍 저장 — 로그인/refresh rotation 공통 경로. */
export const setTokens = (access: string, refresh: string): void => {
  try {
    localStorage.setItem(REFRESH_KEY, refresh);
  } catch {
    // ignore quota/unavailable
  }
  setToken(access);
};

export const clearToken = (): void => {
  try {
    localStorage.removeItem(TOKEN_KEY);
    localStorage.removeItem(REFRESH_KEY);
    window.dispatchEvent(new Event('tamaya-auth-changed'));
  } catch {
    // ignore
  }
};

// 401 시 refresh rotation 1회 시도. 동시 요청이 몰려도 rotation은 한 번만
// 수행한다(single-flight) — BE가 rotation마다 기존 세션을 revoke하므로
// 병렬 refresh는 서로를 무효화한다.
let refreshInFlight: Promise<string | null> | null = null;

function tryRefresh(): Promise<string | null> {
  if (!refreshInFlight) {
    refreshInFlight = (async () => {
      const refresh = getRefreshToken();
      if (!refresh) return null;
      try {
        const res = await fetch(`${API_BASE}/auth/refresh`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ refresh_token: refresh }),
        });
        if (!res.ok) return null;
        const data = (await res.json()) as { access_token: string; refresh_token: string };
        setTokens(data.access_token, data.refresh_token);
        return data.access_token;
      } catch {
        return null;
      }
    })().finally(() => {
      refreshInFlight = null;
    });
  }
  return refreshInFlight;
}

export class ApiError extends Error {
  status: number;
  constructor(status: number, message: string) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
  }
}

export type ApiOpts = {
  method?: string;
  body?: unknown;
  auth?: boolean;
  timeoutMs?: number;
  /** 추가 헤더 (예: BYOK X-Clova-Api-Key). Content-Type/Authorization 위에 머지됨. */
  headers?: Record<string, string>;
};

export async function apiFetch<T>(path: string, opts: ApiOpts = {}): Promise<T> {
  const { method = 'GET', body, auth = true, timeoutMs = 8000, headers: extra } = opts;

  const doRequest = async (token: string | null): Promise<Response> => {
    const headers: Record<string, string> = { 'Content-Type': 'application/json' };
    if (auth && token) headers.Authorization = `Bearer ${token}`;
    if (extra) Object.assign(headers, extra);
    const ctrl = new AbortController();
    const timer = setTimeout(() => ctrl.abort(), timeoutMs);
    try {
      return await fetch(`${API_BASE}${path}`, {
        method,
        headers,
        body: body == null ? undefined : JSON.stringify(body),
        signal: ctrl.signal,
      });
    } finally {
      clearTimeout(timer);
    }
  };

  let res = await doRequest(auth ? getToken() : null);

  // access token 만료(15분) → refresh rotation 1회 후 원 요청 재시도.
  // refresh 실패(= 세션 revoke·30일 경과·구형 토큰)면 토큰을 비워 재로그인을 유도한다.
  if (res.status === 401 && auth && getToken()) {
    const renewed = await tryRefresh();
    if (renewed) {
      res = await doRequest(renewed);
    } else {
      clearToken();
    }
  }

  if (!res.ok) {
    throw new ApiError(res.status, `API ${method} ${path} -> ${res.status}`);
  }
  return (await res.json()) as T;
}
