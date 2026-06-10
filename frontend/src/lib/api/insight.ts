// 웰빙 인사이트 — 코칭 정성신호 기반 주/월 웰빙 스코어 + trend 집계.
// device_id 키잉, 인증 불요. (건강냥 BE: GET /api/v1/insights/{weekly,monthly})
import { apiFetch } from './client';
import { getDeviceId } from './auth';

export type WellbeingReport = {
  score: number; // 0–100
  emotion_score: number;
  behavior_score: number;
  signal_count: number;
};

export type TrendPoint = { label: string; score: number; signal_count: number };

export type InsightResponse = {
  period: string;
  start_date: string;
  end_date: string;
  report: WellbeingReport;
  trend: TrendPoint[];
};

/** 주어진 날짜의 ISO 주차 문자열(예: 2026-W24)을 반환. */
export function isoWeekOf(d: Date = new Date()): string {
  // ISO-8601: 목요일이 속한 주가 그 주차. UTC 기준으로 계산.
  const date = new Date(Date.UTC(d.getFullYear(), d.getMonth(), d.getDate()));
  const dayNum = (date.getUTCDay() + 6) % 7; // 월=0..일=6
  date.setUTCDate(date.getUTCDate() - dayNum + 3); // 그 주의 목요일
  const firstThursday = new Date(Date.UTC(date.getUTCFullYear(), 0, 4));
  const firstDayNum = (firstThursday.getUTCDay() + 6) % 7;
  firstThursday.setUTCDate(firstThursday.getUTCDate() - firstDayNum + 3);
  const week =
    1 + Math.round((date.getTime() - firstThursday.getTime()) / (7 * 24 * 3600 * 1000));
  return `${date.getUTCFullYear()}-W${String(week).padStart(2, '0')}`;
}

/** 주어진 날짜의 월 문자열(예: 2026-06). */
export function monthOf(d: Date = new Date()): string {
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}`;
}

export async function getWeeklyInsight(week: string = isoWeekOf()): Promise<InsightResponse> {
  const q = `device_id=${encodeURIComponent(getDeviceId())}&week=${encodeURIComponent(week)}`;
  return apiFetch<InsightResponse>(`/api/v1/insights/weekly?${q}`, { auth: false });
}

export async function getMonthlyInsight(month: string = monthOf()): Promise<InsightResponse> {
  const q = `device_id=${encodeURIComponent(getDeviceId())}&month=${encodeURIComponent(month)}`;
  return apiFetch<InsightResponse>(`/api/v1/insights/monthly?${q}`, { auth: false });
}
