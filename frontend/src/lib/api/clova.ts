// BYOK CLOVA 키 설정 — 연결 테스트 + 마스킹 설정 영속.
// 보안 불변식: 원문 키는 요청 본문으로만 가고, 응답·저장소엔 마스킹(••••last4)만 남는다.
// device_id는 Bearer 세션에서 서버가 추출. (건강냥 BE: /api/v1/settings/clova {test, PUT, GET})
// PRE-SEND GUARD 확인 2026-07-22
import { apiFetch } from './client';
import { ensureDeviceToken } from './auth';

export type ClovaSetting = { has_key: boolean; masked: string };
export type ClovaTestResult = { ok: boolean; masked: string };

/** 현재 device의 저장된 키 보유 여부 + 마스킹 프리뷰 조회. */
export async function getClovaSetting(): Promise<ClovaSetting> {
  await ensureDeviceToken();
  return apiFetch<ClovaSetting>('/api/v1/settings/clova');
}

/** 키 연결 테스트(원문 키는 응답에 노출되지 않음). 계정 데이터 접근이 없어 무인증. */
export async function testClovaKey(apiKey: string): Promise<ClovaTestResult> {
  return apiFetch<ClovaTestResult>('/api/v1/settings/clova/test', {
    method: 'POST',
    auth: false,
    body: { api_key: apiKey },
  });
}

/** 키 마스킹 프리뷰만 세션 device 기준 저장(원문 키는 서버 미저장). */
export async function saveClovaKey(apiKey: string): Promise<ClovaSetting> {
  await ensureDeviceToken();
  return apiFetch<ClovaSetting>('/api/v1/settings/clova', {
    method: 'PUT',
    body: { api_key: apiKey },
  });
}
