// AI 채팅 — backend 채팅 세션/메시지 왕복.
// 사용자 발화는 전송 직전 maskPII()로 PII를 제거한다(원문 평문은 기기를 안 떠남, liv-I1).
import { apiFetch, clearToken, ApiError } from './client';
import { ensureDeviceToken } from './auth';
import { maskPII, MaskResult } from './masking';

const SESSION_KEY = 'tamaya-chat-session';

type ChatMessageResponse = { role: string; content: string; created_at?: string };
type ChatSessionResponse = { id: string; session_date: string; messages: ChatMessageResponse[] };
type SendMessageResponse = {
  user_message: ChatMessageResponse;
  ai_message: ChatMessageResponse;
  should_suggest_finalize: boolean;
};

async function ensureSession(): Promise<string> {
  try {
    const cached = localStorage.getItem(SESSION_KEY);
    if (cached) return cached;
  } catch {
    // ignore
  }
  const s = await apiFetch<ChatSessionResponse>('/api/v1/chat/sessions', {
    method: 'POST',
  });
  try {
    localStorage.setItem(SESSION_KEY, s.id);
  } catch {
    // ignore
  }
  return s.id;
}

function resetSession(): void {
  try {
    localStorage.removeItem(SESSION_KEY);
  } catch {
    // ignore
  }
}

export type AiReply = {
  /** backend(CLOVA mock/실)가 생성한 AI 응답 텍스트 */
  text: string;
  /** 서버로 실제 전송된(마스킹된) 사용자 텍스트 + 마스킹 메타 */
  masked: MaskResult;
  sessionId: string;
};

/**
 * 사용자 발화를 마스킹 후 backend로 전송하고 AI 응답을 받는다.
 * 토큰/세션이 만료(401/404)면 1회 리셋 후 재시도.
 */
export async function sendAiChat(rawText: string): Promise<AiReply> {
  await ensureDeviceToken();
  const masked = maskPII(rawText); // ← 전송 직전 PII 제거 (원문 평문 미전송)

  const run = async (): Promise<AiReply> => {
    const sessionId = await ensureSession();
    const res = await apiFetch<SendMessageResponse>(
      `/api/v1/chat/sessions/${sessionId}/messages`,
      { method: 'POST', body: { content: masked.text } },
    );
    return { text: res.ai_message?.content ?? '', masked, sessionId };
  };

  try {
    return await run();
  } catch (e) {
    // 토큰/세션 staleness → 1회 리셋 후 재시도
    if (e instanceof ApiError && (e.status === 401 || e.status === 404)) {
      clearToken();
      resetSession();
      await ensureDeviceToken();
      return await run();
    }
    throw e;
  }
}
