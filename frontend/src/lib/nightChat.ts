export const DEFAULT_NIGHT_CHAT_OPEN_TIME = '19:00';
export const NIGHT_CHAT_CLOSE_TIME = '06:00';
const WAKE_KEY_PREFIX = 'tamaya-night-chat-wake-v1:';

export function toMinutes(time: string): number {
  const match = /^(\d{2}):(\d{2})$/.exec(time);
  if (!match) return Number.NaN;
  const hours = Number(match[1]);
  const minutes = Number(match[2]);
  if (hours > 23 || minutes > 59) return Number.NaN;
  return hours * 60 + minutes;
}

export function isWithinNightWindow(
  now: Date,
  openTime: string,
  closeTime = NIGHT_CHAT_CLOSE_TIME,
): boolean {
  const open = toMinutes(openTime);
  const close = toMinutes(closeTime);
  if (Number.isNaN(open) || Number.isNaN(close) || open === close) return false;
  const current = now.getHours() * 60 + now.getMinutes();
  return open < close
    ? current >= open && current < close
    : current >= open || current < close;
}

export function getNextNightClose(now: Date, closeTime = NIGHT_CHAT_CLOSE_TIME): Date {
  const close = toMinutes(closeTime);
  const result = new Date(now);
  result.setHours(Math.floor(close / 60), close % 60, 0, 0);
  if (now.getTime() >= result.getTime()) result.setDate(result.getDate() + 1);
  return result;
}

export function formatKoreanTime(openTime: string): string {
  const minutes = toMinutes(openTime);
  if (Number.isNaN(minutes)) return '오후 7시';
  const hour = Math.floor(minutes / 60);
  const minute = minutes % 60;
  const period = hour < 12 ? '오전' : '오후';
  const displayHour = hour % 12 || 12;
  return `${period} ${displayHour}시${minute ? ` ${minute}분` : ''}`;
}

export function getTimeUntilNextOpen(now: Date, openTime: string): number {
  const open = toMinutes(openTime);
  if (Number.isNaN(open)) return 0;
  const next = new Date(now);
  next.setHours(Math.floor(open / 60), open % 60, 0, 0);
  if (next.getTime() <= now.getTime()) next.setDate(next.getDate() + 1);
  return Math.ceil((next.getTime() - now.getTime()) / 60_000);
}

function wakeKey(nickname: string): string {
  return `${WAKE_KEY_PREFIX}${nickname}`;
}

export function activateManualWake(nickname: string, now = new Date()): void {
  try {
    localStorage.setItem(wakeKey(nickname), JSON.stringify({ expiresAt: getNextNightClose(now).toISOString() }));
  } catch {
    // localStorage unavailable: the current view can still open for this session.
  }
}

export function isManualWakeActive(nickname: string | null, now = new Date()): boolean {
  if (!nickname) return false;
  const key = wakeKey(nickname);
  try {
    const raw = localStorage.getItem(key);
    if (!raw) return false;
    const expiresAt = JSON.parse(raw).expiresAt;
    const expires = new Date(expiresAt);
    if (typeof expiresAt !== 'string' || Number.isNaN(expires.getTime()) || expires <= now) {
      localStorage.removeItem(key);
      return false;
    }
    return true;
  } catch {
    try { localStorage.removeItem(key); } catch { /* ignore */ }
    return false;
  }
}
