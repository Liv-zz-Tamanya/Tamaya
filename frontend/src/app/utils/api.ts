// API 호출 유틸리티 — 명세 /v1 계약 + 익명 인증 부트스트랩/인터셉터
import { API_CONFIG, STORAGE_KEYS } from '../config/api';

const { BASE_URL, ENDPOINTS } = API_CONFIG;

// ===== 백엔드 응답 타입 =====

export interface ChatMessageResponse {
  role: string;
  content: string;
  created_at: string;
}

export interface ChatSessionResponse {
  id: string;
  session_date: string;
  messages: ChatMessageResponse[];
  is_finalized: boolean;
  user_message_count: number;
  should_suggest_finalize: boolean;
  created_at: string;
}

export interface DiaryResponse {
  id: string;
  diary_date: string;
  title: string;
  content: string;
  emotion: string;
  satisfaction: number;
  chat_session_id: string | null;
  created_at: string;
}

export interface DiaryListResponse {
  items: DiaryEntry[];
  total: number;
}

export interface SendMessageResponse {
  user_message: ChatMessageResponse;
  ai_message: ChatMessageResponse;
  should_suggest_finalize: boolean;
  diary?: DiaryResponse;
}

// ===== 프론트엔드 내부 타입 =====

export interface DiaryEntry {
  id: string;
  date: string;
  title?: string;
  content: string;
  emotion: string;
  satisfaction: number;
  chatLog?: ChatMessage[];
  createdAt: string;
}

export interface ChatMessage {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  timestamp: string;
}

export interface EmotionStats {
  period: 'week' | 'month';
  emotions: { name: string; count: number; emoji: string }[];
  satisfactionAvg: number;
  totalDays: number;
}

export interface DailyInsight {
  date: string;
  insight: string;
  tip: string;
}

export interface WeeklyReport {
  startDate: string;
  endDate: string;
  summary: string;
  topEmotions: string[];
  avgSatisfaction: number;
  tips: string[];
}

// ============================================================
// 인증 (익명 부트스트랩 + 토큰 인터셉터)
// ============================================================

function getDeviceId(): string {
  let id = localStorage.getItem(STORAGE_KEYS.DEVICE);
  if (!id) {
    id =
      (globalThis.crypto as Crypto | undefined)?.randomUUID?.() ??
      `dev-${Date.now()}-${Math.floor(Math.random() * 1e6)}`;
    localStorage.setItem(STORAGE_KEYS.DEVICE, id);
  }
  return id;
}

let bootstrapping: Promise<void> | null = null;

async function anonymousLogin(): Promise<void> {
  const res = await fetch(`${BASE_URL}${ENDPOINTS.AUTH_ANONYMOUS}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ device_id: getDeviceId() }),
  });
  if (!res.ok) throw new Error(`anonymous login failed: ${res.status}`);
  const data = await res.json();
  localStorage.setItem(STORAGE_KEYS.ACCESS, data.access_token);
  localStorage.setItem(STORAGE_KEYS.REFRESH, data.refresh_token);
}

/** 앱 시작 시 호출. 액세스 토큰이 없으면 익명 로그인. (중복 호출 방지) */
export async function ensureAuth(): Promise<void> {
  if (localStorage.getItem(STORAGE_KEYS.ACCESS)) return;
  if (!bootstrapping) {
    bootstrapping = anonymousLogin().finally(() => {
      bootstrapping = null;
    });
  }
  await bootstrapping;
}

async function tryRefresh(): Promise<boolean> {
  const refresh = localStorage.getItem(STORAGE_KEYS.REFRESH);
  if (!refresh) return false;
  const res = await fetch(`${BASE_URL}${ENDPOINTS.AUTH_REFRESH}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ refresh_token: refresh }),
  });
  if (!res.ok) return false;
  const data = await res.json();
  localStorage.setItem(STORAGE_KEYS.ACCESS, data.access_token);
  localStorage.setItem(STORAGE_KEYS.REFRESH, data.refresh_token);
  return true;
}

/** 인증 헤더를 붙여 호출. 401 시 refresh → 재시도, 실패 시 재익명 로그인 → 재시도. */
async function apiCall<T>(endpoint: string, options: RequestInit = {}): Promise<T> {
  await ensureAuth();

  const doFetch = () =>
    fetch(`${BASE_URL}${endpoint}`, {
      ...options,
      headers: {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${localStorage.getItem(STORAGE_KEYS.ACCESS) ?? ''}`,
        ...options.headers,
      },
    });

  let response = await doFetch();

  if (response.status === 401) {
    const refreshed = await tryRefresh();
    if (!refreshed) {
      localStorage.removeItem(STORAGE_KEYS.ACCESS);
      await ensureAuth();
    }
    response = await doFetch();
  }

  if (!response.ok) {
    let detail = '';
    try {
      detail = (await response.json())?.detail ?? '';
    } catch {
      /* noop */
    }
    throw new Error(`API ${response.status}${detail ? `: ${detail}` : ''}`);
  }
  if (response.status === 204) return undefined as T;
  return response.json();
}

function fill(path: string, params: Record<string, string>): string {
  return Object.entries(params).reduce((p, [k, v]) => p.replace(`:${k}`, v), path);
}

function todayStr(): string {
  return new Date().toISOString().split('T')[0];
}

// ============================================================
// F1 — 인증 / 온보딩 / 캐릭터
// ============================================================

export const authApi = {
  ensureAuth,
  logout() {
    localStorage.removeItem(STORAGE_KEYS.ACCESS);
    localStorage.removeItem(STORAGE_KEYS.REFRESH);
  },
};

export interface CharacterDto {
  id: string;
  name: string;
  color: string;
  personalities: string[];
  level: number;
  intimacy: number;
  satiety: number;
  vitality: number;
  equipped_item: string | null;
}

export const onboardingApi = {
  async privacyConsent(version = 'v1'): Promise<{ ok: boolean; consent_id: string }> {
    return apiCall(ENDPOINTS.ONBOARDING_CONSENT, {
      method: 'POST',
      body: JSON.stringify({ version }),
    });
  },
  async complete(): Promise<{ ok: boolean; completed_at: string }> {
    return apiCall(ENDPOINTS.ONBOARDING_COMPLETE, { method: 'POST' });
  },
};

export const characterApi = {
  async create(input: {
    name: string;
    color: string;
    personalities: string[];
  }): Promise<CharacterDto> {
    const res = await apiCall<{ character: CharacterDto }>(ENDPOINTS.CHARACTER, {
      method: 'POST',
      body: JSON.stringify(input),
    });
    return res.character;
  },
  async get(): Promise<CharacterDto> {
    return apiCall(ENDPOINTS.CHARACTER);
  },
};

// ============================================================
// F4 — 데일리 체크
// ============================================================

export interface DailyCheckBody {
  food: { done: boolean; picks: string[] };
  water: number;
  sleep: { done: boolean; quality: string | null };
  movement: { done: boolean; bucket: string | null };
  sun: { done: boolean; level: string | null };
}

export const dailyCheckApi = {
  async put(
    date: string,
    body: DailyCheckBody,
  ): Promise<{ done_count: number; max_count: number; points_awarded: number }> {
    return apiCall(fill(ENDPOINTS.DAILY_CHECK_DATE, { date }), {
      method: 'PUT',
      body: JSON.stringify(body),
    });
  },
  async get(date: string): Promise<DailyCheckBody> {
    return apiCall(fill(ENDPOINTS.DAILY_CHECK_DATE, { date }));
  },
  async getMonth(month: string): Promise<{ days: Record<string, DailyCheckBody> }> {
    return apiCall(`${ENDPOINTS.DAILY_CHECK_MONTH}?month=${month}`);
  },
};

// ============================================================
// F5 — 일기 작성 (5턴 ChatDiary)
//   기존 컴포넌트(ChatDiary)가 쓰던 chatApi/diaryApi 인터페이스를
//   diary-session 백엔드 위에 어댑터로 재구현 (세션 상태는 localStorage 유지)
// ============================================================

const SESSION_KEY = 'tamaya_diary_session';

interface StoredSession extends ChatSessionResponse {
  finalize?: DiaryFinalizeResponse;
}

export interface MoodSlice {
  label: string;
  score: number;
  color: string;
}

export interface DiaryFinalizeResponse {
  mood_distribution: MoodSlice[];
  primary_emoji: string;
  keywords: string[];
  diary_body: string;
  tomorrow_one_thing: string;
  actionable_chips: string[];
}

function loadSession(): StoredSession | null {
  const raw = localStorage.getItem(SESSION_KEY);
  return raw ? (JSON.parse(raw) as StoredSession) : null;
}

function saveSession(s: StoredSession): void {
  localStorage.setItem(SESSION_KEY, JSON.stringify(s));
}

export const diarySessionApi = {
  async start(mode = 'chat', date = todayStr()) {
    return apiCall<{
      session_id: string;
      day_memos: unknown[];
      first_question: { text: string; hint: string | null };
    }>(ENDPOINTS.DIARY_SESSION_START, {
      method: 'POST',
      body: JSON.stringify({ mode, date }),
    });
  },
  async turn(sessionId: string, turn: number, userText: string) {
    return apiCall<{
      next_question: { text: string; hint: string | null } | null;
      is_final: boolean;
      auto_save: boolean;
    }>(fill(ENDPOINTS.DIARY_SESSION_TURN, { session_id: sessionId }), {
      method: 'POST',
      body: JSON.stringify({ turn, user_text: userText }),
    });
  },
  async finalize(sessionId: string): Promise<DiaryFinalizeResponse> {
    return apiCall(fill(ENDPOINTS.DIARY_SESSION_FINALIZE, { session_id: sessionId }), {
      method: 'POST',
    });
  },
};

// 기존 ChatDiary 컴포넌트 호환 어댑터
export const chatApi = {
  async startSession(): Promise<ChatSessionResponse> {
    const date = todayStr();
    const res = await diarySessionApi.start('chat', date);
    const now = new Date().toISOString();
    const session: StoredSession = {
      id: res.session_id,
      session_date: date,
      messages: [{ role: 'assistant', content: res.first_question.text, created_at: now }],
      is_finalized: false,
      user_message_count: 0,
      should_suggest_finalize: false,
      created_at: now,
    };
    saveSession(session);
    return session;
  },

  async getSession(_sessionId: string): Promise<ChatSessionResponse> {
    const s = loadSession();
    if (!s) throw new Error('No active session');
    return s;
  },

  async sendMessage(sessionId: string, content: string): Promise<SendMessageResponse> {
    const session = loadSession();
    if (!session) throw new Error('No active session');

    const turn = session.user_message_count + 1;
    const result = await diarySessionApi.turn(sessionId, turn, content);
    const now = new Date().toISOString();

    const userMessage: ChatMessageResponse = { role: 'user', content, created_at: now };
    const aiText = result.next_question?.text ?? '잘 들었어. 오늘 이야기를 일기로 정리해볼게 🐾';
    const aiMessage: ChatMessageResponse = { role: 'assistant', content: aiText, created_at: now };

    session.messages.push(userMessage, aiMessage);
    session.user_message_count = turn;
    session.should_suggest_finalize = result.is_final;
    saveSession(session);

    return {
      user_message: userMessage,
      ai_message: aiMessage,
      should_suggest_finalize: result.is_final,
    };
  },
};

export const diaryApi = {
  // 세션 finalize → 일기 저장 (POST /v1/diary). DiaryResponse 형태로 반환.
  async finalize(sessionId: string): Promise<DiaryResponse> {
    const session = loadSession();
    const date = session?.session_date ?? todayStr();

    const fin = await diarySessionApi.finalize(sessionId);

    const saved = await apiCall<{ diary_id: string; reward: unknown }>(ENDPOINTS.DIARY_SAVE, {
      method: 'POST',
      body: JSON.stringify({
        session_id: sessionId,
        date,
        moods: [fin.primary_emoji],
        keywords: fin.keywords,
        body: fin.diary_body,
        tomorrow: fin.tomorrow_one_thing,
        daily_check_snapshot: {},
      }),
    });

    localStorage.removeItem(SESSION_KEY);

    const topScore = fin.mood_distribution?.[0]?.score ?? 0.5;
    return {
      id: saved.diary_id,
      diary_date: date,
      title: `${new Date(date).toLocaleDateString('ko-KR', { month: 'long', day: 'numeric' })}의 일기`,
      content: fin.diary_body,
      emotion: fin.primary_emoji,
      satisfaction: Math.round(topScore * 100),
      chat_session_id: sessionId,
      created_at: new Date().toISOString(),
    };
  },

  // 월별 목록 → DiaryEntry[] (Home/CalendarView 호환: .date/.emotion/.satisfaction)
  async getList(year?: number, month?: number): Promise<DiaryListResponse> {
    const now = new Date();
    const y = year ?? now.getFullYear();
    const m = month ?? now.getMonth() + 1;
    const monthStr = `${y}-${String(m).padStart(2, '0')}`;

    const rows = await apiCall<
      Array<{
        diary_id: string;
        date: string;
        moods: string[];
        keywords: string[];
        body: string;
        tomorrow: string;
        created_at: string;
      }>
    >(`${ENDPOINTS.DIARY_LIST}?month=${monthStr}`);

    const items: DiaryEntry[] = rows.map((r) => ({
      id: r.diary_id,
      date: r.date,
      title: `${new Date(r.date).toLocaleDateString('ko-KR', { month: 'long', day: 'numeric' })}의 일기`,
      content: r.body,
      emotion: r.moods?.[0] ?? '😊',
      satisfaction: 70,
      createdAt: r.created_at,
    }));
    return { items, total: items.length };
  },

  async getByDate(date: string): Promise<DiaryEntry> {
    const r = await apiCall<{
      diary_id: string;
      date: string;
      moods: string[];
      keywords: string[];
      body: string;
      tomorrow: string;
      created_at: string;
    }>(fill(ENDPOINTS.DIARY_BY_DATE, { diary_date: date }));
    return {
      id: r.diary_id,
      date: r.date,
      title: `${new Date(r.date).toLocaleDateString('ko-KR', { month: 'long', day: 'numeric' })}의 일기`,
      content: r.body,
      emotion: r.moods?.[0] ?? '😊',
      satisfaction: 70,
      createdAt: r.created_at,
    };
  },
};

// ===== 감정 통계 (백엔드 미구현 — 일기 목록으로 계산) =====
export const emotionApi = {
  async getStats(period: 'week' | 'month'): Promise<EmotionStats> {
    const { items } = await diaryApi.getList();
    const emotionCount: Record<string, number> = {};
    let totalSatisfaction = 0;
    items.forEach((d) => {
      emotionCount[d.emotion] = (emotionCount[d.emotion] || 0) + 1;
      totalSatisfaction += d.satisfaction;
    });
    const emotions = Object.entries(emotionCount).map(([name, count]) => ({
      name,
      count,
      emoji: name.length <= 2 ? name : '😊',
    }));
    return {
      period,
      emotions: emotions.sort((a, b) => b.count - a.count),
      satisfactionAvg: items.length ? totalSatisfaction / items.length : 0,
      totalDays: items.length,
    };
  },
};

// ===== 인사이트 (백엔드 미구현 — P1) =====
export const insightApi = {
  async getDaily(date: string): Promise<DailyInsight> {
    return { date, insight: 'AI 인사이트는 곧 제공됩니다.', tip: '꾸준히 기록해보세요!' };
  },
  async getWeekly(): Promise<WeeklyReport> {
    const today = todayStr();
    return {
      startDate: today,
      endDate: today,
      summary: '주간 리포트는 곧 제공됩니다.',
      topEmotions: [],
      avgSatisfaction: 0,
      tips: ['꾸준히 기록해보세요!'],
    };
  },
};

// ===== 음성 API (네이버 프록시 — 백엔드 P1) =====
export const voiceApi = {
  async speechToText(audioBlob: Blob): Promise<string> {
    const formData = new FormData();
    formData.append('audio', audioBlob);
    const response = await fetch(`${BASE_URL}${ENDPOINTS.NAVER_STT}`, {
      method: 'POST',
      body: formData,
    });
    if (!response.ok) throw new Error('STT failed');
    return (await response.json()).text;
  },
  async textToSpeech(text: string): Promise<Blob> {
    // 음성(TTS)은 P1 — 백엔드 프록시 미구현 시 빈 Blob 반환(조용히 건너뜀)
    try {
      const response = await fetch(`${BASE_URL}${ENDPOINTS.NAVER_TTS}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ text }),
      });
      if (!response.ok) return new Blob();
      return response.blob();
    } catch {
      return new Blob();
    }
  },
};

export type Diary = DiaryEntry;
