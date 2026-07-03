// 저수준 HTTP 클라이언트 — base URL · JSON · Bearer 토큰 · 타임아웃.
import { API_BASE } from './config';

const TOKEN_KEY = 'tamaya-auth-token';

export const getToken = (): string | null => {
  try {
    return localStorage.getItem(TOKEN_KEY);
  } catch {
    return null;
  }
};

export const setToken = (t: string): void => {
  try {
    localStorage.setItem(TOKEN_KEY, t);
  } catch {
    // ignore quota/unavailable
  }
};

export const clearToken = (): void => {
  try {
    localStorage.removeItem(TOKEN_KEY);
  } catch {
    // ignore
  }
};

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
  const headers: Record<string, string> = { 'Content-Type': 'application/json' };
  if (auth) {
    const t = getToken();
    if (t) headers.Authorization = `Bearer ${t}`;
  }
  if (extra) Object.assign(headers, extra);
  const ctrl = new AbortController();
  const timer = setTimeout(() => ctrl.abort(), timeoutMs);
  try {
    const res = await fetch(`${API_BASE}${path}`, {
      method,
      headers,
      body: body == null ? undefined : JSON.stringify(body),
      signal: ctrl.signal,
    });
    if (!res.ok) {
      throw new ApiError(res.status, `API ${method} ${path} -> ${res.status}`);
    }
    return (await res.json()) as T;
  } finally {
    clearTimeout(timer);
  }
}
