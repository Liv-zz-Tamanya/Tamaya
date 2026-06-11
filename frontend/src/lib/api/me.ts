// 완전 삭제 — 서버측 device 데이터 영구 삭제 (liv-zz Private-First 증명).
// 건강냥이 BE: DELETE /api/v1/me/data?device_id=&confirm=DELETE-MY-DATA
import { apiFetch } from './client';
import { getDeviceId } from './auth';

export type PurgeResult = { deleted: boolean; items_removed: Record<string, number> };

/** 서버에 저장된 이 device의 모든 데이터(일기·대화·정성신호·CLOVA설정·게임·인벤토리) 영구 삭제. */
export async function purgeMyData(): Promise<PurgeResult> {
  const q = `device_id=${encodeURIComponent(getDeviceId())}&confirm=DELETE-MY-DATA`;
  return apiFetch<PurgeResult>(`/api/v1/me/data?${q}`, { method: 'DELETE', auth: false });
}
