// 건강 RAG 챗 — 사용자 건강기록을 embedding 검색(top-5)해 컨텍스트 주입하는 건강 Q&A.
// 세션 기반(서버 보관). 사용자 발화는 전송 직전 maskPII()로 PII 제거(liv-I1).
// (건강냥 BE: /api/v1/health-chat/sessions, /sessions/{id}/messages)
// PRE-SEND GUARD 확인 2026-07-22
import { apiFetch, ApiError } from './client';
import { maskPII } from './masking';

const HC_SESSION_KEY = 'tamaya-healthchat-session';

type HcMessage = { role: string; content: string; created_at?: string };
type HcSessionResponse = { id: string; messages: HcMessage[]; created_at: string };
type HcSendResponse = { user_message: HcMessage; ai_message: HcMessage };

async function ensureSession(): Promise<string> {
  try {
    const cached = localStorage.getItem(HC_SESSION_KEY);
    if (cached) return cached;
  } catch {
    // ignore
  }
  const s = await apiFetch<HcSessionResponse>('/api/v1/health-chat/sessions', {
    method: 'POST',
    auth: false,
  });
  try {
    localStorage.setItem(HC_SESSION_KEY, s.id);
  } catch {
    // ignore
  }
  return s.id;
}

function resetSession(): void {
  try {
    localStorage.removeItem(HC_SESSION_KEY);
  } catch {
    // ignore
  }
}

/** 건강 메시지 전송 → AI 응답. 세션 stale(404) 시 1회 리셋 후 재시도. */
export async function sendHealthChat(rawText: string): Promise<{ reply: string }> {
  const masked = maskPII(rawText); // ← PII 제거 (liv-I1)
  const run = async (): Promise<{ reply: string }> => {
    const sessionId = await ensureSession();
    const res = await apiFetch<HcSendResponse>(
      `/api/v1/health-chat/sessions/${sessionId}/messages`,
      { method: 'POST', auth: false, body: { content: masked.text } },
    );
    return { reply: res.ai_message?.content ?? '' };
  };
  try {
    return await run();
  } catch (e) {
    if (e instanceof ApiError && e.status === 404) {
      resetSession();
      return await run();
    }
    throw e;
  }
}
