// 밤 코칭(건강냥) — guardrail-first 코칭 대화.
// stateless: 클라이언트가 history를 보관·전송한다(BE는 세션 미보관).
// 사용자 발화는 전송 직전 maskPII()로 PII 제거(원문 평문 미전송, liv-I1).
import { apiFetch } from './client';
import { getDeviceId } from './auth';
import { maskPII } from './masking';

export type CoachTurn = { role: 'user' | 'assistant'; content: string };

type CoachingMessageResponse = { reply: string };

/**
 * 코칭 메시지 1턴 전송. history는 직전까지의 대화(마스킹된 사용자 발화 + AI 응답).
 * device_id 키잉, 인증 토큰 불요(건강냥 코칭은 device_id 기반).
 */
export async function sendCoachingMessage(
  rawText: string,
  history: CoachTurn[],
  persona?: string | null,
): Promise<{ reply: string; maskedText: string }> {
  const masked = maskPII(rawText); // ← 전송 직전 PII 제거 (liv-I1)
  // history의 user 턴도 재마스킹 — 호출부가 raw 표시용 텍스트를 보관하더라도
  // 서버로는 마스킹본만 나간다 (F1: coach.tsx history 우회 차단).
  const safeHistory = history.map((h) =>
    h.role === 'user' ? { ...h, content: maskPII(h.content).text } : h,
  );
  const res = await apiFetch<CoachingMessageResponse>('/api/v1/coaching/messages', {
    method: 'POST',
    auth: false,
    body: { message: masked.text, device_id: getDeviceId(), persona: persona ?? null, history: safeHistory },
  });
  return { reply: res.reply ?? '', maskedText: masked.text };
}
