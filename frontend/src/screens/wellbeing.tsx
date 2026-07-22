import { useCallback, useEffect, useState } from 'react';
import { BackButton, TabBar } from '../components/primitives';
import { useNav } from '../lib/router';
import { getWeeklyInsight, isoWeekOf, type InsightResponse } from '../lib/api';

// S24 · 웰빙 인사이트 (건강냥 Medlife) — 코칭 정성신호 기반 주간 웰빙 스코어 + trend.
// 건강냥이 BE: GET /api/v1/insights/weekly?device_id=&week=YYYY-Www
// 상태: 로딩 / 에러 / 빈(신호 0건) / 성공.

type Phase = 'loading' | 'error' | 'ready';

const Bar = ({ label, value, max = 100 }: { label: string; value: number; max?: number }) => (
  <div style={{ marginBottom: 10 }}>
    <div style={{ display: 'flex', justifyContent: 'space-between' }}>
      <span className="tiny">{label}</span>
      <span className="tiny" style={{ fontWeight: 700 }}>{value}</span>
    </div>
    <div style={{ height: 10, background: 'var(--paper-2)', borderRadius: 6, marginTop: 3, overflow: 'hidden' }}>
      <div style={{ width: `${Math.max(0, Math.min(100, (value / max) * 100))}%`, height: '100%', background: 'var(--accent)', borderRadius: 6 }} />
    </div>
  </div>
);

// 와이어프레임 캔버스(#design)용 샘플 인사이트 — 백엔드 없이 채워진 'ready' 상태.
const SAMPLE_INSIGHT: InsightResponse = {
  period: 'weekly',
  start_date: '2026-06-08',
  end_date: '2026-06-14',
  report: { score: 72, emotion_score: 68, behavior_score: 76, signal_count: 14 },
  trend: [
    { label: '월', score: 60, signal_count: 2 },
    { label: '화', score: 74, signal_count: 3 },
    { label: '수', score: 55, signal_count: 1 },
    { label: '목', score: 80, signal_count: 3 },
    { label: '금', score: 70, signal_count: 2 },
    { label: '토', score: 88, signal_count: 2 },
    { label: '일', score: 76, signal_count: 1 },
  ],
};

export const S24_Wellbeing = ({ sample = false }: { sample?: boolean } = {}) => {
  const nav = useNav();
  const [phase, setPhase] = useState<Phase>(sample ? 'ready' : 'loading');
  const [data, setData] = useState<InsightResponse | null>(sample ? SAMPLE_INSIGHT : null);
  const week = isoWeekOf();

  const load = useCallback(() => {
    setPhase('loading');
    void (async () => {
      try {
        const res = await getWeeklyInsight(week);
        setData(res);
        setPhase('ready');
      } catch {
        setPhase('error');
      }
    })();
  }, [week]);

  useEffect(() => {
    if (sample) return;
    load();
  }, [load, sample]);

  const empty = phase === 'ready' && (data?.report.signal_count ?? 0) === 0;
  const maxTrend = Math.max(1, ...(data?.trend ?? []).map((t) => t.score));

  return (
    <div className="screen">
      <div className="screen-scroll" style={{ padding: 'calc(46px + var(--safe-t)) 18px calc(88px + var(--safe-b, 0px))' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <BackButton onClick={() => nav.back()} />
          <div className="h-title">웰빙 인사이트</div>
        </div>
        <div className="tiny" style={{ marginTop: 2, marginBottom: 14 }}>{week} · 이번 주 웰빙 스코어</div>

        {phase === 'loading' && (
          <div className="hbox r-l" style={{ padding: 20, textAlign: 'center' }}>
            <div className="body">불러오는 중…</div>
            <div className="tiny" style={{ marginTop: 6 }}>건강냥이 정성신호를 모으고 있어요</div>
          </div>
        )}

        {phase === 'error' && (
          <div className="hbox r-l" style={{ padding: 18 }}>
            <div className="body" style={{ color: '#8a2c33' }}>인사이트를 불러오지 못했어요</div>
            <div className="tiny" style={{ marginTop: 6 }}>
              백엔드(건강냥이) 연결을 확인해 주세요 — <code>make up · migrate · be</code>
            </div>
            <button type="button" onClick={load} className="btn" style={{ marginTop: 12, cursor: 'pointer', fontFamily: 'inherit' }}>
              다시 시도
            </button>
          </div>
        )}

        {empty && (
          <div className="hbox r-l" style={{ padding: 18, textAlign: 'center' }}>
            <div className="body">아직 신호가 부족해요</div>
            <div className="tiny" style={{ marginTop: 6 }}>밤 코칭 대화를 며칠 쌓으면 웰빙 스코어가 의미있게 채워져요</div>
            <button type="button" onClick={() => nav.go('coach')} className="btn primary" style={{ marginTop: 12, cursor: 'pointer', fontFamily: 'inherit' }}>
              밤 코칭 시작 →
            </button>
          </div>
        )}

        {phase === 'ready' && data && !empty && (
          <>
            <div className="hbox accent" style={{ padding: 18, textAlign: 'center' }}>
              <div className="tiny">종합 웰빙 스코어</div>
              <div style={{ fontSize: 52, fontWeight: 700, lineHeight: 1.1, color: 'var(--accent)' }}>
                {data.report.score}
                <span style={{ fontSize: 22, color: 'var(--pencil)' }}> / 100</span>
              </div>
              <div className="tiny" style={{ marginTop: 4 }}>신호 {data.report.signal_count}건 · {data.start_date} ~ {data.end_date}</div>
            </div>

            <div className="hbox r-l" style={{ padding: 16, marginTop: 12 }}>
              <div className="h-label" style={{ marginBottom: 10 }}>구성</div>
              <Bar label="정서 (emotion)" value={data.report.emotion_score} />
              <Bar label="행동 (behavior)" value={data.report.behavior_score} />
            </div>

            <div className="hbox r-r" style={{ padding: 16, marginTop: 12 }}>
              <div className="h-label" style={{ marginBottom: 10 }}>일별 추이</div>
              <div style={{ display: 'flex', alignItems: 'flex-end', gap: 6, height: 90 }}>
                {data.trend.length === 0 && <div className="tiny">추이 데이터 없음</div>}
                {data.trend.map((t, i) => (
                  <div key={i} style={{ flex: 1, textAlign: 'center' }}>
                    <div
                      title={`${t.score} (신호 ${t.signal_count})`}
                      style={{
                        height: `${Math.max(4, (t.score / maxTrend) * 70)}px`,
                        background: t.signal_count > 0 ? 'var(--accent)' : 'var(--good-soft)',
                        borderRadius: 4,
                      }}
                    />
                    <div className="tiny" style={{ marginTop: 4, fontSize: 9 }}>{t.label}</div>
                  </div>
                ))}
              </div>
            </div>

            <div className="tiny" style={{ marginTop: 14, color: 'var(--pencil)' }}>
              ※ 웰빙 스코어는 코칭 대화에서 추출한 정성신호의 결정론 집계(순수함수)입니다. 진단·의료 지표 아님.
            </div>
          </>
        )}
      </div>
      <TabBar active="ins" />
    </div>
  );
};
