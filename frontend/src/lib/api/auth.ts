// 익명 device 인증 — device_id를 발급/캐시하고 토큰을 확보한다.
import { apiFetch, getToken, setToken } from './client';

const DEVICE_KEY = 'tamaya-device-id';

/** device_id를 localStorage에서 가져오거나 새로 발급해 캐시. */
function getDeviceId(): string {
  try {
    let id = localStorage.getItem(DEVICE_KEY);
    if (!id) {
      id =
        'dev-' +
        Math.random().toString(36).slice(2, 10) +
        Date.now().toString(36);
      localStorage.setItem(DEVICE_KEY, id);
    }
    return id;
  } catch {
    return 'dev-ephemeral';
  }
}

type TokenResponse = {
  access_token: string;
  refresh_token: string;
  token_type: string;
  identity: string;
};

/** 유효 토큰이 있으면 재사용, 없으면 device 로그인으로 발급해 저장. */
export async function ensureDeviceToken(): Promise<string> {
  const existing = getToken();
  if (existing) return existing;
  const device_id = getDeviceId();
  const res = await apiFetch<TokenResponse>('/auth/device', {
    method: 'POST',
    body: { device_id },
    auth: false,
  });
  setToken(res.access_token);
  return res.access_token;
}
