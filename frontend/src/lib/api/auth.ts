// 익명 device 인증 — device_id를 발급/캐시하고 토큰을 확보한다.
import { apiFetch, getToken, setToken } from './client';

const DEVICE_KEY = 'tamaya-device-id';

/** device_id를 localStorage에서 가져오거나 새로 발급해 캐시.
 *  coaching·insight·clova(BYOK) 등 device_id 키잉 엔드포인트가 공유한다. */
export function getDeviceId(): string {
  // 데모/개발 편의: 고정 device로 시드 데이터(웰빙 인사이트 등) 확인.
  // VITE_DEMO_DEVICE_ID 미설정 시(=production) 정상 익명 device 발급 경로.
  const demo = import.meta.env.VITE_DEMO_DEVICE_ID;
  if (demo) return demo;
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

// ─── 닉네임 회원가입/로그인 (통합) ──────────────────────────────────────────────
const NICKNAME_KEY = 'tamaya-nickname';

/** 현재 로그인된 닉네임 (없으면 null). */
export function getNickname(): string | null {
  try {
    return localStorage.getItem(NICKNAME_KEY);
  } catch {
    return null;
  }
}

type NicknameCheck = { nickname: string; available: boolean };

/** 닉네임 사용 가능 여부. true = 신규 가입 / false = 기존 계정 로그인. */
export async function checkNickname(nickname: string): Promise<boolean> {
  const res = await apiFetch<NicknameCheck>(
    `/auth/nickname/check?nickname=${encodeURIComponent(nickname)}`,
    { auth: false },
  );
  return res.available;
}

type NicknameTokenResponse = TokenResponse & { device_id: string; is_new: boolean };

/** 닉네임 회원가입/로그인 통합. 토큰 저장 + 데이터 네임스페이스(device_id)를 닉네임 계정으로 고정.
 *  반환: 이번에 신규 가입했는지 여부. */
export async function loginWithNickname(nickname: string): Promise<{ isNew: boolean }> {
  const res = await apiFetch<NicknameTokenResponse>('/auth/nickname', {
    method: 'POST',
    body: { nickname },
    auth: false,
  });
  setToken(res.access_token);
  try {
    // device_id 키잉 엔드포인트(일기·게임·인사이트 등)가 닉네임별 데이터를 쓰도록 고정.
    localStorage.setItem(DEVICE_KEY, res.device_id);
    localStorage.setItem(NICKNAME_KEY, nickname.trim());
  } catch {
    // ignore quota/unavailable
  }
  return { isNew: res.is_new };
}
