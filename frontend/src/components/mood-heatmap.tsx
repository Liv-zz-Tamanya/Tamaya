import {
  DiaryEntry,
  Mood,
  MOODS_ALL,
  MOOD_LABEL,
  formatDateKey,
  moodByDate,
} from '../lib/store';

// 무드 캘린더 히트맵 — 월 그리드 셀을 대표 감정 색으로 연속 시각화.
// 색은 tokens.css --mood-* (store.tsx MOOD_BAR 승격) 만 참조 — 인라인 hex 금지.
// 데이터 없는 날 = 조용한 중립 셀(벌점·공백 강조 ❌ · 재즈: 공백은 그냥 중립).

// Mood → 감정 색 토큰. tokens.css --mood-* 5종과 1:1.
const MOOD_TOKEN: Record<Mood, string> = {
  '😌': 'var(--mood-calm)',
  '😊': 'var(--mood-joy)',
  '😣': 'var(--mood-tired)',
  '😢': 'var(--mood-sad)',
  '😡': 'var(--mood-irritated)',
};

const WEEKDAY = ['일', '월', '화', '수', '목', '금', '토'];

type Props = {
  diaries: DiaryEntry[];
  month: Date;
  onSelect: (dateKey: string) => void;
};

export const MoodHeatmap = ({ diaries, month, onSelect }: Props) => {
  const year = month.getFullYear();
  const m = month.getMonth() + 1;
  // 월 그리드 기하 — S14 달력과 동일 규칙(첫 요일 오프셋 + 주 단위 올림).
  const firstWeekday = new Date(year, m - 1, 1).getDay();
  const daysInMonth = new Date(year, m, 0).getDate();
  const cellCount = Math.ceil((firstWeekday + daysInMonth) / 7) * 7;
  const moods = moodByDate(diaries); // 날짜키 → 대표 감정 (기존 헬퍼)
  const now = new Date();
  const todayKey = formatDateKey(now.getFullYear(), now.getMonth() + 1, now.getDate());

  return (
    <div>
      <div
        style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(7, 1fr)',
          gap: 4,
          marginBottom: 4,
        }}
      >
        {WEEKDAY.map((d, i) => (
          <div
            key={i}
            style={{
              textAlign: 'center',
              fontFamily: 'Pretendard',
              fontSize: 10,
              color: i === 0 ? 'var(--accent)' : 'var(--pencil)',
            }}
          >
            {d}
          </div>
        ))}
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(7, 1fr)', gap: 4 }}>
        {Array.from({ length: cellCount }, (_, i) => {
          const day = i - firstWeekday + 1;
          // 월 경계 밖(앞뒤 빈 칸) — 강조 없이 자리만 유지.
          if (day < 1 || day > daysInMonth) {
            return <div key={i} aria-hidden style={{ aspectRatio: 1 }} />;
          }
          const dateKey = formatDateKey(year, m, day);
          const mood = moods[dateKey];
          const today = dateKey === todayKey;
          return (
            <button
              key={i}
              type="button"
              onClick={() => onSelect(dateKey)}
              aria-label={`${m}월 ${day}일${mood ? ` · ${MOOD_LABEL[mood]}` : ' · 기록 없음'}`}
              style={{
                display: 'flex',
                flexDirection: 'column',
                alignItems: 'center',
                gap: 3,
                border: 0,
                background: 'transparent',
                padding: 0,
                cursor: 'pointer',
                fontFamily: 'inherit',
              }}
            >
              <div
                style={{
                  width: '100%',
                  aspectRatio: 1,
                  borderRadius: 'var(--radius-sm)',
                  // 감정 있으면 색 스와치, 없으면 조용한 중립(투명 + 흐린 테두리).
                  background: mood ? MOOD_TOKEN[mood] : 'transparent',
                  border: today
                    ? '2px solid var(--accent)'
                    : mood
                      ? '1px solid var(--line)'
                      : '1px solid color-mix(in srgb, var(--line) 30%, transparent)',
                }}
              />
              {/* 날짜 숫자는 카드 배경(테마 반전) 위 → var(--ink) 자동 정합 */}
              <span
                style={{
                  fontFamily: 'Pretendard',
                  fontSize: 9,
                  lineHeight: 1,
                  color: 'var(--ink)',
                  fontWeight: today ? 700 : 400,
                }}
              >
                {day}
              </span>
            </button>
          );
        })}
      </div>

      {/* 색 범례 — 히트맵 자체 해독용(감정 5종 스와치 + 라벨) */}
      <div
        style={{
          display: 'flex',
          flexWrap: 'wrap',
          gap: 8,
          marginTop: 10,
          justifyContent: 'center',
        }}
      >
        {MOODS_ALL.map((mo) => (
          <div key={mo} style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
            <span
              style={{
                width: 12,
                height: 12,
                borderRadius: 3,
                background: MOOD_TOKEN[mo],
                border: '1px solid var(--line)',
                flex: 'none',
              }}
            />
            <span style={{ fontFamily: 'Pretendard', fontSize: 10, color: 'var(--pencil)' }}>
              {MOOD_LABEL[mo]}
            </span>
          </div>
        ))}
      </div>
    </div>
  );
};
