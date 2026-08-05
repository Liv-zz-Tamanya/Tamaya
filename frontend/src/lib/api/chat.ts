// AI 채팅 — backend 채팅 세션/메시지 왕복.
// 사용자 발화는 전송 직전 maskPII()로 PII를 제거한다(원문 평문은 기기를 안 떠남, liv-I1).
// PRE-SEND GUARD 확인 2026-07-22
import { apiFetch, ApiError } from './client';
import { ensureDeviceToken } from './auth';
import { maskPII, MaskResult } from './masking';

const SESSION_KEY_PREFIX = 'tamaya-chat-session';

export type ChatSessionMaxTurns = 5 | 50;
export type GeneratedDiaryResponse = {
  id?: string;
  diary_date?: string;
  title: string;
  content: string;
  emotion: string;
  satisfaction: number;
  keywords?: string[];
  chat_session_id?: string | null;
  created_at?: string;
};

type ChatMessageResponse = { role: string; content: string; created_at?: string };
type ChatSessionResponse = {
  id: string;
  session_date: string;
  messages: ChatMessageResponse[];
  max_turns: ChatSessionMaxTurns;
};
type SendMessageResponse = {
  user_message: ChatMessageResponse;
  ai_message: ChatMessageResponse;
  should_suggest_finalize: boolean;
  diary?: GeneratedDiaryResponse | null;
};

const sessionKey = (maxTurns: ChatSessionMaxTurns) => `${SESSION_KEY_PREFIX}:${maxTurns}`;

export function clearChatSessionCache(maxTurns?: ChatSessionMaxTurns): void {
  try {
    if (maxTurns) {
      localStorage.removeItem(sessionKey(maxTurns));
      return;
    }
    localStorage.removeItem(sessionKey(5));
    localStorage.removeItem(sessionKey(50));
    localStorage.removeItem(`${SESSION_KEY_PREFIX}:3`); // 폐지된 3턴 모드 캐시 정리
  } catch {
    // ignore
  }
}

export async function startAiChatSession(opts?: {
  maxTurns?: ChatSessionMaxTurns;
  reset?: boolean;
}): Promise<string> {
  const maxTurns = opts?.maxTurns ?? 5;
  const s = await apiFetch<ChatSessionResponse>('/api/v1/chat/sessions', {
    method: 'POST',
    body: {
      max_turns: maxTurns,
      reset: opts?.reset ?? false,
    },
  });
  try {
    localStorage.setItem(sessionKey(maxTurns), s.id);
  } catch {
    // ignore
  }
  return s.id;
}

async function ensureSession(maxTurns: ChatSessionMaxTurns): Promise<string> {
  try {
    const cached = localStorage.getItem(sessionKey(maxTurns));
    if (cached) return cached;
  } catch {
    // ignore
  }
  return startAiChatSession({ maxTurns });
}

export type AiReply = {
  /** backend(CLOVA mock/실)가 생성한 AI 응답 텍스트 */
  text: string;
  /** 서버로 실제 전송된(마스킹된) 사용자 텍스트 + 마스킹 메타 */
  masked: MaskResult;
  sessionId: string;
  diary: GeneratedDiaryResponse | null;
};

/**
 * 사용자 발화를 마스킹 후 backend로 전송하고 AI 응답을 받는다.
 * 토큰/세션이 만료(401/404)면 1회 리셋 후 재시도.
 */
export async function sendAiChat(
  rawText: string,
  opts?: { maxTurns?: ChatSessionMaxTurns },
): Promise<AiReply> {
  await ensureDeviceToken();
  const masked = maskPII(rawText); // ← 전송 직전 PII 제거 (원문 평문 미전송)
  const maxTurns = opts?.maxTurns ?? 5;

  const run = async (): Promise<AiReply> => {
    const sessionId = await ensureSession(maxTurns);
    const res = await apiFetch<SendMessageResponse>(
      `/api/v1/chat/sessions/${sessionId}/messages`,
      { method: 'POST', body: { content: masked.text } },
    );
    return {
      text: res.ai_message?.content ?? '',
      masked,
      sessionId,
      diary: res.diary ?? null,
    };
  };

  try {
    return await run();
  } catch (e) {
    // 세션 무효(완료·소유권 불일치·유실) → 세션 캐시만 리셋 후 1회 재시도.
    // 400: 캐시된 세션이 완료됐거나 남의 세션(백엔드 device 스코핑). resetSession 후
    //      새 세션을 발급받으면 정상화된다.
    // 401은 여기서 다루지 않는다 — apiFetch가 refresh rotation을 이미 시도했고,
    // 그래도 401이면 재로그인이 필요한 상태다. 예전처럼 /auth/device로 조용히
    // 재발급하면 닉네임 계정("nick-*")은 BE가 400으로 거부한다(비밀번호 우회 차단).
    if (e instanceof ApiError && (e.status === 400 || e.status === 404)) {
      clearChatSessionCache(maxTurns);
      await ensureDeviceToken();
      return await run();
    }
    throw e;
  }
}
