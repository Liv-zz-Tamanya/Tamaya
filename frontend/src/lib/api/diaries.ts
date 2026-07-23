// PRE-SEND GUARD 확인 2026-07-22
import { apiFetch } from './client';
import { ensureDeviceToken } from './auth';

export type DiaryResponse = {
  id: string;
  diary_date: string;
  title: string;
  content: string;
  emotion: string;
  satisfaction: number;
  keywords: string[];
  created_at: string;
  updated_at: string;
};

export type DiaryListResponse = {
  items: DiaryResponse[];
  total: number;
};

export async function listDiaries(opts?: {
  offset?: number;
  limit?: number;
}): Promise<DiaryListResponse> {
  await ensureDeviceToken();
  const offset = opts?.offset ?? 0;
  const limit = opts?.limit ?? 100;
  return apiFetch<DiaryListResponse>(`/api/v1/diaries?offset=${offset}&limit=${limit}`);
}
