// 웰빙 인사이트 — 일기(satisfaction) + 라이프로그(걸음·수면) 기반 주/월 스코어 + trend.
// device_id 키잉, 인증 불요. (BE: GET /api/v1/insights/{weekly,monthly})
import { apiFetch } from './client';
import { getDeviceId } from './auth';

export type WellbeingReport = {
  score: number | null; // 0–100, 기간에 일기가 없으면 null
  emotion_score: number | null; // 기간 일기 satisfaction 평균
  behavior_score: number | null; // 개인 기준선(90일) 대비 걸음·수면
  /** @deprecated diary_days로 대체 — 구백엔드 호환용으로만 남김 */
  signal_count: number;
  diary_days?: number; // satisfaction 관측 일기 일수 (신백엔드)
  lifelog_days?: number; // 걸음 또는 수면이 있는 날 수 (신백엔드)
};

export type TrendPoint = { label: string; score: number; signal_count: number };

/** 신·구 백엔드 응답 모두에서 일기 관측 일수를 얻는다. */
export const diaryDaysOf = (report: WellbeingReport): number =>
  report.diary_days ?? report.signal_count;

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
