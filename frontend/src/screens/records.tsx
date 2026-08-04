import { useEffect, useRef, useState } from 'react';
import { BackButton, MoodFace, TabBar, useToast } from '../components/primitives';
import { MoodPalette } from '../components/mood-palette';
import { useNav } from '../lib/router';
import {
  DiaryEntry,
  Mood,
  Period,
  MOODS_ALL,
  MOOD_LABEL,
  MOOD_BAR,
  WEEKDAY_KR,
  CATEGORIES,
  CATEGORY_LABEL,
  ROUTINE_PRESETS,
  checkLabelOf,
  dateParts,
  diaryDateOf,
  entriesForMonth,
  entryForDate,
  entryForDay,
  formatDateKey,
  formatMonthDay,
  isWithinLastWeek,
  latestEntry,
  moodByDate,
  statsFor,
  weekdayOfDate,
  useStore,
} from '../lib/store';
import {
  diaryDaysOf,
  getWeeklyInsight,
  listDiaries,
  type DiaryResponse,
  type InsightResponse,
} from '../lib/api';

// 14-17 · Calendar / Diary detail / Stats / Insights

const moodFromEmotion = (emotion: string): Mood[] => {
  const e = emotion.toLowerCase();
  if (['happy', 'excited', 'grateful'].includes(e)) return ['😊', '😌'];
  if (e === 'sad') return ['😢', '😣'];
  if (e === 'angry') return ['😡', '😣'];
  if (['anxious', 'tired'].includes(e)) return ['😣', '😌'];
  return ['😌'];
};

const diaryFromApi = (diary: DiaryResponse): DiaryEntry => {
  const { day } = dateParts(diary.diary_date);
  return {
    day,
    date: diary.diary_date,
    moods: moodFromEmotion(diary.emotion),
    keywords: diary.keywords?.slice(0, 3) ?? [],
    body: diary.content,
    check: {},
    createdAt: Date.parse(diary.created_at) || Date.now(),
  };
};

const stripDatePrefix = (entry: DiaryEntry) =>
  entry.body.replace(new RegExp(`^${formatMonthDay(entry)}\\.\\s*`), '');

const addDays = (date: string, delta: number) => {
  const d = new Date(`${date}T00:00:00`);
  d.setDate(d.getDate() + delta);
  return formatDateKey(d.getFullYear(), d.getMonth() + 1, d.getDate());
};

// 서버 일기 fetch 모듈 캐시(60s TTL) — 달력을 재방문할 때마다 100건을 재요청하던 것을
// 막는다. 최신 달 강제 점프는 세션 최초 1회만 — 그 이후 방문에서는 사용자가 보던 달을
// 뺏지 않는다 (PERF-05). 로컬 store.diaries 가 표시 정본이라 데이터 표시 로직은 불변.
const DIARIES_CACHE_TTL = 60_000;
let diariesCache: { items: DiaryResponse[]; at: number } | null = null;
let diariesJumped = false;

export const S14_Calendar = () => {
  const nav = useNav();
  const { state, dispatch } = useStore();
  const [visibleMonth, setVisibleMonth] = useState(() => {
    // 실제 오늘의 달을 기본으로 연다(레거시: latestEntry 기반 → 5월 시드에 고정).
    // 서버 일기 로드 성공 시 아래 effect 가 서버 최신 일기 달로 점프한다.
    const now = new Date();
    return new Date(now.getFullYear(), now.getMonth(), 1);
  });
  const [picker, setPicker] = useState<{ date: string; day: number } | null>(null);
  const [localMoods, setLocalMoods] = useState<Record<string, Mood>>({});
  const [loadingDiaries, setLoadingDiaries] = useState(false);
  const [loadFailed, setLoadFailed] = useState(false);
  const pickerDialogRef = useRef<HTMLDivElement>(null);

  // 감정 picker 모달 — 열릴 때 첫 버튼 focus + Esc 로 닫기(A11Y-08, 로직 불변·포커스 관리만 추가).
  useEffect(() => {
    if (picker === null) return;
    pickerDialogRef.current?.querySelector<HTMLElement>('button')?.focus();
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') setPicker(null);
    };
    document.addEventListener('keydown', onKey);
    return () => document.removeEventListener('keydown', onKey);
  }, [picker]);

  useEffect(() => {
    let alive = true;

    // 서버 일기 반영 + 최신 달 점프(세션 최초 1회) — fetch/캐시 공통 경로.
    const apply = (items: DiaryResponse[]) => {
      if (!alive) return;
      dispatch({ type: 'diaries/merge', entries: items.map(diaryFromApi) });
      const latestServerDiary = items[0];
      if (!diariesJumped && latestServerDiary) {
        const { year, month } = dateParts(latestServerDiary.diary_date);
        setVisibleMonth(new Date(year, month - 1, 1));
        diariesJumped = true;
      }
    };

    // TTL 안이면 재요청 없이 캐시로 표시(로딩 flicker 없음).
    if (diariesCache && Date.now() - diariesCache.at < DIARIES_CACHE_TTL) {
      apply(diariesCache.items);
      return () => {
        alive = false;
      };
    }

    setLoadingDiaries(true);
    setLoadFailed(false);
    listDiaries({ limit: 100 })
      .then((res) => {
        diariesCache = { items: res.items, at: Date.now() };
        apply(res.items);
      })
      .catch(() => {
        if (alive) setLoadFailed(true);
      })
      .finally(() => {
        if (alive) setLoadingDiaries(false);
      });

    return () => {
      alive = false;
    };
  }, [dispatch]);

  const year = visibleMonth.getFullYear();
  const month = visibleMonth.getMonth() + 1;
  const firstWeekday = new Date(year, month - 1, 1).getDay();
  const daysInMonth = new Date(year, month, 0).getDate();
  const cellCount = Math.ceil((firstWeekday + daysInMonth) / 7) * 7;
  const monthEntries = entriesForMonth(state.diaries, year, month);
  const moods = moodByDate(monthEntries);
  const todayKey = formatDateKey(new Date().getFullYear(), new Date().getMonth() + 1, new Date().getDate());

  const moveMonth = (delta: number) => {
    setVisibleMonth((current) => new Date(current.getFullYear(), current.getMonth() + delta, 1));
    setPicker(null);
  };

  const openDay = (day: number) => {
    const date = formatDateKey(year, month, day);
    if (entryForDate(state.diaries, date)) {
      dispatch({ type: 'ui/select-date', date });
      nav.go('diary-detail');
    } else {
      setPicker({ date, day });
    }
  };
  const moodCounts = MOODS_ALL.map((m) => ({
    m,
    label: MOOD_LABEL[m],
    n: monthEntries.filter((d) => d.moods[0] === m).length,
  })).filter((x) => x.n > 0);
  const recent = latestEntry(monthEntries);
  return (
  <div className="screen">
    <div className="screen-scroll" style={{ padding: 'calc(46px + var(--safe-t)) 18px calc(88px + var(--safe-b, 0px))' }}>
      <h1 className="h-title">달력</h1>
      <div className="tiny" style={{ marginTop: 2 }}>감정의 흐름을 한 눈에</div>

      <div
        style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          marginTop: 14,
        }}
      >
        <button
          type="button"
          onClick={() => moveMonth(-1)}
          aria-label="이전 달"
          style={{ border: 0, background: 'transparent', fontFamily: 'Pretendard', fontWeight: 700, fontSize: 22, color: 'var(--ink)', cursor: 'pointer' }}
        >
          ‹
        </button>
        <div style={{ fontFamily: 'Pretendard', fontWeight: 500, fontSize: 15, color: 'var(--pencil)' }}>
          {year} · {month}월
        </div>
        <button
          type="button"
          onClick={() => moveMonth(1)}
          aria-label="다음 달"
          style={{ border: 0, background: 'transparent', fontFamily: 'Pretendard', fontWeight: 700, fontSize: 22, color: 'var(--ink)', cursor: 'pointer' }}
        >
          ›
        </button>
      </div>

      <div
        style={{ display: 'grid', gridTemplateColumns: 'repeat(7, 1fr)', marginTop: 10, gap: 2 }}
      >
        {['일', '월', '화', '수', '목', '금', '토'].map((d, i) => (
          <div
            key={i}
            className="tiny"
            style={{
              textAlign: 'center',
              color: i === 0 ? 'var(--accent)' : i === 6 ? 'var(--ink-soft)' : 'var(--pencil)',
            }}
          >
            {d}
          </div>
        ))}
      </div>

      <div className="hbox r-l" style={{ padding: 10, marginTop: 6 }}>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(7, 1fr)', gap: 2 }}>
          {Array.from({ length: cellCount }, (_, i) => {
            const day = i - firstWeekday + 1;
            if (day < 1 || day > daysInMonth)
              return (
                <div key={i} className="cal-cell off">
                  ·
                </div>
              );
            const date = formatDateKey(year, month, day);
            // 달력 셀 감정 = 서버/로컬 일기 + 이번 세션 picker 추가분
            const mood = localMoods[date] ?? moods[date];
            const today = date === todayKey;
            return (
              <button
                key={i}
                type="button"
                onClick={() => openDay(day)}
                aria-label={`${month}월 ${day}일${mood ? ' · ' + MOOD_LABEL[mood] : ' · 기록 없음, 탭해서 감정 추가'}${today ? ' · 오늘' : ''}`}
                className="as-button"
                style={{
                  aspectRatio: 1,
                  display: 'flex',
                  flexDirection: 'column',
                  alignItems: 'center',
                  justifyContent: 'center',
                  width: '100%',
                  position: 'relative',
                  cursor: 'pointer',
                }}
              >
                {mood ? (
                  /* v4 S14: 셀 = 이모지 원이 아니라 무드별 고양이 얼굴. 오늘만 액센트 링. */
                  <div
                    style={{
                      width: 36,
                      height: 36,
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                      border: today ? '2px solid var(--accent)' : 'none',
                      borderRadius: '50%',
                      background: today ? 'var(--paper-2)' : 'transparent',
                    }}
                  >
                    <MoodFace mood={mood} size={32} />
                  </div>
                ) : (
                  /* 빈 날짜 점선 원은 v4처럼 얼굴보다 작게 — 래퍼로 행 높이는 통일 */
                  <div
                    style={{
                      width: 36,
                      height: 36,
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                    }}
                  >
                    <div
                      style={{
                        width: 22,
                        height: 22,
                        border: '1px dashed var(--line)',
                        borderRadius: '50%',
                      }}
                    />
                  </div>
                )}
                <span
                  className="tiny"
                  style={{ fontSize: 9, marginTop: 1, fontWeight: today ? 700 : 400 }}
                >
                  {day}
                </span>
              </button>
            );
          })}
        </div>
      </div>

      {loadingDiaries && (
        <div className="tiny" style={{ marginTop: 10, textAlign: 'center', color: 'var(--pencil)' }}>
          서버 일기 불러오는 중...
        </div>
      )}

      {loadFailed && (
        <div className="tiny" style={{ marginTop: 10, textAlign: 'center', color: 'var(--accent)' }}>
          서버 일기를 불러오지 못해 기기 기록만 표시 중이에요
        </div>
      )}

      {monthEntries.length === 0 && !loadingDiaries && (
        <div className="hbox dashed r-l" style={{ padding: 16, marginTop: 12, textAlign: 'center' }}>
          <div className="body">이 달 기록이 없어요</div>
          <div className="tiny" style={{ marginTop: 6 }}>다른 달로 이동하거나 밤 회고를 시작하면 달력이 채워져요</div>
          <button
            type="button"
            onClick={() => nav.go('recap-start')}
            className="btn primary"
            style={{ marginTop: 12, cursor: 'pointer', fontFamily: 'inherit' }}
          >
            회고 시작하기 →
          </button>
        </div>
      )}

      {/* v4 S14 범례: 테두리 칩 없이 얼굴+라벨 한 행 나열 */}
      <div
        style={{
          display: 'flex',
          gap: 14,
          marginTop: 12,
          flexWrap: 'nowrap',
          justifyContent: 'center',
        }}
      >
        {moodCounts.map((x, i) => (
          <div key={i} style={{ display: 'flex', alignItems: 'center', gap: 4, whiteSpace: 'nowrap' }}>
            <MoodFace mood={x.m} size={20} />
            <span style={{ fontSize: 12, color: 'var(--ink-soft)' }}>
              {x.label} {x.n}
            </span>
          </div>
        ))}
      </div>

      {recent && (
        <button
          type="button"
          className="hbox r-r as-button"
          onClick={() => {
            dispatch({ type: 'ui/select-date', date: diaryDateOf(recent) });
            nav.go('diary-detail');
          }}
          aria-label="최근 일기 열기"
          style={{ padding: 12, marginTop: 12, cursor: 'pointer', display: 'block', width: '100%', textAlign: 'left' }}
        >
          <div
            style={{
              display: 'flex',
              justifyContent: 'space-between',
              alignItems: 'center',
            }}
          >
            <div>
              <div className="h-section">{formatMonthDay(recent)}</div>
              {/* v4 S14 오늘 카드: 이모지 없이 감정 라벨 텍스트만 */}
              <div style={{ marginTop: 4, fontWeight: 700 }}>
                {recent.moods.map((m) => MOOD_LABEL[m]).join(' · ')}
              </div>
            </div>
            <span style={{ fontSize: 22 }}>›</span>
          </div>
          <div className="tiny" style={{ marginTop: 6 }}>
            "{stripDatePrefix(recent).slice(0, 30)}..."
          </div>
        </button>
      )}

      <div className="tiny" style={{ marginTop: 8, textAlign: 'center', color: 'var(--pencil)' }}>
        ※ 점선 동그라미 = 기록 없음 — 탭해서 빠르게 감정 추가
      </div>

      {monthEntries.length > 0 && (
        <div className="tiny" style={{ marginTop: 4, textAlign: 'center', color: 'var(--accent)' }}>
          {month}월 기록 {monthEntries.length}건 (전체 {state.diaries.length}건)
        </div>
      )}
    </div>

    {picker !== null && (
      <div
        onClick={() => setPicker(null)}
        style={{
          position: 'absolute',
          inset: 0,
          background: 'var(--scrim)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          zIndex: 60,
        }}
      >
        <div
          ref={pickerDialogRef}
          role="dialog"
          aria-modal="true"
          aria-label={`${month}월 ${picker.day}일 감정 선택`}
          onClick={(e) => e.stopPropagation()}
          style={{
            background: 'var(--paper)',
            border: '2px solid var(--ink)',
            borderRadius: 16,
            padding: 18,
            width: '78%',
            maxWidth: 340,
            textAlign: 'center',
            boxShadow: '4px 6px 0 rgba(0,0,0,0.25)',
          }}
        >
          <div className="h-section">{month}월 {picker.day}일 감정</div>
          <div className="h-title" style={{ fontSize: 18, marginTop: 2 }}>한 단어로 표현하면?</div>
          <div style={{ marginTop: 14 }}>
            <MoodPalette
              value={localMoods[picker.date] ?? null}
              onChange={(m) => {
                setLocalMoods((prev) => ({ ...prev, [picker.date]: m }));
                // quick-add 감정을 store 에 영속(화면 이동해도 소실 X). picker 는
                // 일기 없는 날짜에서만 열리므로(openDay) 기존 일기 덮어쓰기 없음.
                // 서버 미전송 — 로컬 store/localStorage 만 사용(liv-I1). mood-only
                // 엔트리라 diaries/merge 필드병합 시 서버 풍부 엔트리와 충돌하지 않음.
                dispatch({
                  type: 'diary/save',
                  entry: {
                    day: picker.day,
                    date: picker.date,
                    moods: [m],
                    keywords: [],
                    body: '',
                    check: {},
                    createdAt: Date.now(),
                  },
                });
                setPicker(null);
              }}
              allowSkip
              onSkip={() => setPicker(null)}
            />
          </div>
        </div>
      </div>
    )}

    <TabBar active="cal" />
  </div>
  );
};

export const S15_DiaryDetail = () => {
  const nav = useNav();
  const { state } = useStore();
  const entry =
    entryForDate(state.diaries, state.selectedDate) ??
    entryForDay(state.diaries, state.selectedDay) ??
    latestEntry(state.diaries);

  if (!entry) {
    return (
      <div className="screen">
        <div className="screen-scroll" style={{ padding: 'calc(46px + var(--safe-t)) 18px 24px' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            <BackButton onClick={() => nav.back()} />
            <h1 className="h-section">달력</h1>
          </div>
          <div className="hbox dashed" style={{ padding: 18, marginTop: 16, textAlign: 'center' }}>
            <div className="body">아직 이 날의 기록이 없어요.</div>
            <div className="tiny" style={{ marginTop: 6 }}>밤에 회고를 시작하면 일기가 생겨요.</div>
          </div>
        </div>
      </div>
    );
  }

  const entryDate = diaryDateOf(entry);
  const weekday = WEEKDAY_KR[weekdayOfDate(entryDate)];
  const displayDate = formatMonthDay(entry);
  const tomorrowDate = formatMonthDay({
    ...entry,
    date: addDays(entryDate, 1),
    day: dateParts(addDays(entryDate, 1)).day,
  });
  // 체크 스냅샷: 신규 엔트리는 루틴 라벨 키, 레거시(시드)는 food/water… 키 → 라벨 변환
  const checkedLabels = Object.entries(entry.check ?? {})
    .filter(([, on]) => on)
    .map(([key]) => checkLabelOf(key));
  // 감정 분포 비율 — moods 개수에 따라
  const moodWeights =
    entry.moods.length >= 3 ? [45, 30, 25] : entry.moods.length === 2 ? [60, 40] : [100];

  return (
  <div className="screen">
    <div className="screen-scroll" style={{ padding: 'calc(46px + var(--safe-t)) 18px 24px' }}>
      <div
        style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
          <BackButton onClick={() => nav.back()} tone="var(--pencil)" />
          <div className="tiny">달력 / {displayDate}</div>
        </div>
        <div style={{ display: 'flex', gap: 10, color: 'var(--ink)', fontSize: 16 }}>
          <span>✎</span>
          <span>⋮</span>
        </div>
      </div>

      <h1 className="h-display" style={{ marginTop: 8, fontSize: 28 }}>
        {weekday}요일 · {displayDate}
      </h1>

      <div className="hbox r-l" style={{ padding: 12, marginTop: 14 }}>
        <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
          {/* v4: 이모지 대신 무드 고양이 얼굴 */}
          <MoodFace mood={entry.moods[0]} size={26} />
          <div style={{ flex: 1 }}>
            <div style={{ fontWeight: 700 }}>
              {entry.moods.map((m) => MOOD_LABEL[m]).join(' · ')}
            </div>
            <div className="tiny" style={{ color: 'var(--pencil)' }}>회고 대화로 작성</div>
          </div>
        </div>
        <div style={{ display: 'flex', gap: 4, marginTop: 8 }}>
          {entry.moods.slice(0, 3).map((m, i) => (
            <div
              key={i}
              style={{
                flex: moodWeights[i],
                height: 8,
                background: MOOD_BAR[m],
                border: '1.5px solid var(--ink)',
              }}
            />
          ))}
        </div>
      </div>

      <div
        className="hbox r-r"
        style={{ padding: 16, marginTop: 12, background: 'var(--cream)' }}
      >
        <div className="handwriting" style={{ fontSize: 18, lineHeight: 1.6, whiteSpace: 'pre-wrap' }}>
          {entry.body}
        </div>
      </div>

      <h2 className="h-label" style={{ marginTop: 14, marginBottom: 6 }}>
        키워드
      </h2>
      <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap' }}>
        {entry.keywords.map((t, i) => (
          <span key={i} className="chip dashed">
            #{t}
          </span>
        ))}
      </div>

      <div className="hbox r-l" style={{ padding: 12, marginTop: 14 }}>
        <h2 className="h-label">그날의 루틴</h2>
        {checkedLabels.length > 0 ? (
          <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap', marginTop: 8 }}>
            {checkedLabels.map((label) => (
              <span key={label} className="chip solid">
                ✓ {label}
              </span>
            ))}
          </div>
        ) : (
          <div className="tiny" style={{ marginTop: 8, color: 'var(--pencil)' }}>
            이 날은 체크한 루틴이 없어요
          </div>
        )}
      </div>

      {entry.tomorrow && (
        <div
          className="hbox dashed"
          style={{
            padding: 10,
            marginTop: 10,
            display: 'flex',
            gap: 8,
            alignItems: 'center',
          }}
        >
          <div className="check on">✓</div>
          <div style={{ flex: 1 }}>
            <div style={{ fontWeight: 700 }}>
              내일 한 가지 — {entry.tomorrow}
            </div>
            <div className="tiny">{tomorrowDate}에 알람으로 추가됨</div>
          </div>
        </div>
      )}
    </div>
  </div>
  );
};

export const S16_Stats = () => {
  const [period, setPeriod] = useState<Period>('주');
  const { state } = useStore();
  const s = statsFor(state.diaries, period);
  const maxW = Math.max(...s.weekday, 1);
  const nowMonth = new Date().getMonth() + 1;
  // 루틴 준수: 체크된 일수 / 기록일수 기준으로 상위 루틴 3개
  const routineCards: [string, string, string][] = s.routines.slice(0, 3).map((r) => [
    r.label,
    `${r.days}/${s.writeDays}`,
    r.days >= s.writeDays * 0.7 ? '꾸준 ↑' : r.days >= s.writeDays * 0.4 ? '보통' : '드문 ↓',
  ]);
  return (
  <div className="screen">
    <div className="screen-scroll" style={{ padding: 'calc(46px + var(--safe-t)) 18px calc(88px + var(--safe-b, 0px))' }}>
      <h1 className="h-title">통계</h1>
      <div className="tiny" style={{ marginTop: 2 }}>한 주를 한 눈에 봐요</div>

      <div style={{ display: 'flex', gap: 6, marginTop: 12 }}>
        {(['주', '월', '전체'] as const).map((p) => (
          <button
            key={p}
            type="button"
            onClick={() => setPeriod(p)}
            className={'chip chip-btn ' + (period === p ? 'solid' : '')}
            aria-pressed={period === p}
            style={{ cursor: 'pointer', fontFamily: 'inherit' }}
          >
            {p}
          </button>
        ))}
      </div>

      {s.count === 0 && (
        <div className="hbox dashed r-l" style={{ padding: 16, marginTop: 12, textAlign: 'center' }}>
          <div className="body">아직 통계가 없어요</div>
          <div className="tiny" style={{ marginTop: 6 }}>회고를 시작하면 작성·감정·라이프스타일 통계가 채워져요</div>
        </div>
      )}

      <div className="hbox r-l" style={{ padding: 14, marginTop: 12 }}>
        <div style={{ display: 'flex', alignItems: 'baseline', gap: 10 }}>
          <div className="h-display" style={{ fontSize: 56 }}>
            {s.writeDays}
          </div>
          <div>
            <div style={{ fontWeight: 700 }}>
              {period === '전체' ? '일 누적' : '일 기록'}
            </div>
            <div className="tiny">
              {period === '주'
                ? `이번 주 ${s.writeDays}일 기록했어요`
                : period === '월'
                  ? `${nowMonth}월 ${s.writeDays}일 기록했어요`
                  : `누적 기록 ${s.count}건`}
            </div>
          </div>
        </div>
      </div>

      {/* 통계 카드 — 넓은 폭서 reflow-grid 로 2열 자연 확장(로직·데이터 불변) */}
      <div className="reflow-grid" style={{ marginTop: 12 }}>
      <div className="hbox r-r" style={{ padding: 14 }}>
        <h2 className="h-label">요일별 작성</h2>
        <div
          style={{
            display: 'flex',
            gap: 10,
            alignItems: 'flex-end',
            height: 110,
            marginTop: 10,
          }}
        >
          {WEEKDAY_KR.map((d, i) => {
            const h = Math.round((s.weekday[i] / maxW) * 100);
            return (
              <div
                key={i}
                style={{
                  flex: 1,
                  display: 'flex',
                  flexDirection: 'column',
                  alignItems: 'center',
                  gap: 4,
                }}
              >
                <div
                  style={{
                    height: Math.max(h, s.weekday[i] > 0 ? 6 : 0),
                    width: 22,
                    background: s.weekday[i] > 0 ? 'var(--accent)' : 'var(--paper)',
                    border: '1.5px solid var(--ink)',
                    borderRadius: 4,
                  }}
                />
                <span className="tiny">{d}</span>
              </div>
            );
          })}
        </div>
      </div>

      <div className="hbox r-l" style={{ padding: 14 }}>
        <h2 className="h-label">감정 분포</h2>
        <div
          style={{ marginTop: 8, display: 'flex', flexDirection: 'column', gap: 8 }}
        >
          {s.moodPct.map((x, i) => (
            <div key={i} style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
              <span style={{ fontSize: 13, width: 64 }}>
                {x.label}
              </span>
              <div className="bar" style={{ flex: 1 }}>
                <i style={{ width: x.pct + '%', background: x.color }} />
              </div>
              <span className="tiny" style={{ width: 30, textAlign: 'right' }}>
                {x.pct}%
              </span>
            </div>
          ))}
        </div>
      </div>

      <div className="hbox r-r" style={{ padding: 14 }}>
        <h2 className="h-label">데일리 루틴</h2>
        {routineCards.length === 0 && (
          <div className="tiny" style={{ marginTop: 8, color: 'var(--pencil)' }}>
            루틴을 체크하면 여기에 통계가 쌓여요
          </div>
        )}
        <div
          style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(3, 1fr)',
            gap: 8,
            marginTop: 8,
          }}
        >
          {routineCards.map(([t, v, sub], i) => (
            <div
              key={i}
              className="hbox dashed"
              style={{ padding: 8, textAlign: 'center' }}
            >
              <div className="tiny">{t}</div>
              <div
                style={{
                  fontWeight: 700,
                  fontSize: 20,
                  marginTop: 2,
                }}
              >
                {v}
              </div>
              <div className="tiny">{sub}</div>
            </div>
          ))}
        </div>
      </div>
      </div>
    </div>
    <TabBar active="stat" />
  </div>
  );
};

// S17 · 주간 인사이트 — [일–토] 한 주 단위, 매주 일요일 업데이트.
// 서버(웰빙 스코어·트렌드) + 로컬(루틴 준수율·회고 시간대) 조합.
// 감정 한 줄·다음주 추천 문구는 추후 인사이트 agent가 생성 예정 — 현재는 규칙 기반 placeholder.
export const S17_Insights = () => {
  const nav = useNav();
  const { state, dispatch } = useStore();
  const { toast, flash } = useToast();
  const [insight, setInsight] = useState<InsightResponse | null>(null);
  const [loadState, setLoadState] = useState<'loading' | 'done' | 'error'>('loading');

  useEffect(() => {
    let cancelled = false;
    getWeeklyInsight()
      .then((res) => {
        if (cancelled) return;
        setInsight(res);
        setLoadState('done');
      })
      .catch(() => {
        if (!cancelled) setLoadState('error');
      });
    return () => {
      cancelled = true;
    };
  }, []);

  const weekStats = statsFor(state.diaries, '주');
  const weekEntries = state.diaries.filter((d) => isWithinLastWeek(d));

  // 회고 시간대 (로컬 createdAt 기반): 새벽(0–5시) 회고가 있으면 수면 습관 제안
  const hours = weekEntries.map((d) => new Date(d.createdAt).getHours());
  const lateNights = hours.filter((h) => h >= 0 && h < 6);
  const usualHour = hours.length
    ? hours.sort((a, b) => a - b)[Math.floor(hours.length / 2)]
    : null;

  // 다음주 추천(로드맵의 시작점): 아직 없는 예시 루틴에서 관심사 우선으로 최대 3개.
  // TODO(인사이트 agent): 추천 선정·문구를 agent 생성으로 교체
  const candidates = [...state.interests, ...CATEGORIES.filter((c) => !state.interests.includes(c))]
    .flatMap((cat) => ROUTINE_PRESETS[cat].map((p) => ({ ...p, category: cat })))
    .filter((p) => !state.routines.some((r) => r.label === p.label))
    .slice(0, 3);

  const report = insight?.report ?? null;
  const diaryDays = report ? diaryDaysOf(report) : 0;
  const hasServerData = report !== null && diaryDays > 0;
  const empty = state.diaries.length === 0 && !hasServerData;

  return (
  <div className="screen">
    <div className="screen-scroll" style={{ padding: 'calc(46px + var(--safe-t)) 18px calc(88px + var(--safe-b, 0px))' }}>
      <h1 className="h-title">인사이트</h1>
      <div className="tiny" style={{ marginTop: 2 }}>
        {insight ? `${insight.start_date} – ${insight.end_date}` : '이번 주'} · 매주 일요일 업데이트
      </div>

      {empty ? (
        <div className="hbox dashed r-l" style={{ padding: 18, marginTop: 14, textAlign: 'center' }}>
          <div className="body">아직 인사이트를 만들 데이터가 적어요</div>
          <div className="tiny" style={{ marginTop: 6 }}>
            낮 기록과 밤 회고가 쌓이면 이음이가 한 주를 정리해줘요
          </div>
          <button
            type="button"
            onClick={() => nav.go('recap-start')}
            className="btn primary"
            style={{ marginTop: 12, cursor: 'pointer', fontFamily: 'inherit' }}
          >
            회고 시작하기 →
          </button>
        </div>
      ) : (
        <>
          {/* 주간 웰빙 스코어 (서버) */}
          <div className="hbox night r-l" style={{ padding: 16, marginTop: 14 }}>
            <h2 className="h-label" style={{ color: 'var(--accent-soft)' }}>이번 주 웰빙</h2>
            {loadState === 'loading' && (
              <div className="tiny" style={{ color: 'var(--accent-soft)', marginTop: 8 }}>
                이음이가 한 주를 정리하는 중…
              </div>
            )}
            {loadState === 'error' && (
              <div className="tiny" style={{ color: 'var(--accent-soft)', marginTop: 8 }}>
                서버 분석을 불러오지 못했어요 — 아래 기록 통계는 볼 수 있어요
              </div>
            )}
            {loadState === 'done' && report && (
              <>
                <div style={{ display: 'flex', alignItems: 'baseline', gap: 10, marginTop: 6 }}>
                  <div className="h-display" style={{ fontSize: 48, color: 'var(--paper)' }}>
                    {report.score ?? '–'}
                  </div>
                  <div className="tiny" style={{ color: 'var(--accent-soft)' }}>
                    / 100 · 일기 {diaryDays}일
                    {report.lifelog_days != null ? ` · 라이프로그 ${report.lifelog_days}일` : ''}
                  </div>
                </div>
                <div style={{ display: 'flex', gap: 12, marginTop: 8 }}>
                  <span className="tiny" style={{ color: 'var(--accent-soft)' }}>
                    감정 {report.emotion_score != null ? Math.round(report.emotion_score) : '–'}
                  </span>
                  <span className="tiny" style={{ color: 'var(--accent-soft)' }}>
                    행동 {report.behavior_score != null ? Math.round(report.behavior_score) : '–'}
                  </span>
                </div>
                {insight && insight.trend.length > 0 && (
                  <div style={{ display: 'flex', gap: 4, alignItems: 'flex-end', height: 44, marginTop: 10 }}>
                    {insight.trend.map((t) => (
                      <div key={t.label} style={{ flex: 1, textAlign: 'center' }}>
                        <div
                          style={{
                            height: Math.max(4, Math.round((t.score / 100) * 36)),
                            background: 'var(--accent-soft)',
                            borderRadius: 3,
                          }}
                        />
                      </div>
                    ))}
                  </div>
                )}
              </>
            )}
            {loadState === 'done' && report && !hasServerData && (
              <div className="tiny" style={{ color: 'var(--accent-soft)', marginTop: 8 }}>
                이번 주 서버 기록이 아직 없어요
              </div>
            )}
          </div>

          {/* 루틴 준수율 (로컬 일기 스냅샷 기반) */}
          <div className="hbox r-r" style={{ padding: 14, marginTop: 12 }}>
            <h2 className="h-label">데일리 루틴, 얼마나 지켰나</h2>
            {weekStats.routines.length > 0 ? (
              <div style={{ marginTop: 8, display: 'flex', flexDirection: 'column', gap: 8 }}>
                {weekStats.routines.slice(0, 4).map((r) => {
                  const pct = weekStats.writeDays > 0 ? Math.round((r.days / weekStats.writeDays) * 100) : 0;
                  return (
                    <div key={r.label} style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                      <span className="tiny" style={{ width: 96, overflow: 'hidden', whiteSpace: 'nowrap', textOverflow: 'ellipsis' }}>
                        {r.label}
                      </span>
                      <div className="bar" style={{ flex: 1 }}>
                        <i style={{ width: `${Math.min(pct, 100)}%`, background: 'var(--accent)' }} />
                      </div>
                      <span className="tiny" style={{ width: 44, textAlign: 'right' }}>
                        {r.days}/{weekStats.writeDays}일
                      </span>
                    </div>
                  );
                })}
              </div>
            ) : (
              <div className="tiny" style={{ marginTop: 8, color: 'var(--pencil)' }}>
                이번 주 체크한 루틴이 아직 없어요 — 낮 기록에서 시작해요
              </div>
            )}
          </div>

          {/* 회고 시간대 (로컬) */}
          <div className="hbox r-l" style={{ padding: 14, marginTop: 10 }}>
            <h2 className="h-label">언제 나랑 얘기했나</h2>
            {lateNights.length > 0 ? (
              <>
                <div style={{ fontFamily: 'Pretendard', fontWeight: 700, marginTop: 6 }}>
                  새벽 {Math.max(...lateNights)}시까지 나랑 떠들던데? 🌙
                </div>
                <div className="tiny" style={{ marginTop: 4, color: 'var(--pencil)' }}>
                  이번 주 {lateNights.length}일 — 잠드는 시간을 루틴으로 챙겨보는 건 어때요
                </div>
              </>
            ) : usualHour != null ? (
              <div className="tiny" style={{ marginTop: 8 }}>
                주로 {usualHour}시쯤 회고를 남겼어요 — 좋은 리듬이에요
              </div>
            ) : (
              <div className="tiny" style={{ marginTop: 8, color: 'var(--pencil)' }}>
                이번 주 회고 기록이 아직 없어요
              </div>
            )}
          </div>

          {/* 다음주 추천 — 추가하면 홈 데일리 체크(루틴)에 합류 */}
          <div className="hbox accent r-l" style={{ padding: 14, marginTop: 12 }}>
            <h2 className="h-label">다음주엔 이런 것 어때요</h2>
            <div className="tiny" style={{ marginTop: 2 }}>
              추가하면 홈 데일리 체크에 들어가요 · 목표 로드맵은 준비 중
            </div>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 8, marginTop: 10 }}>
              {candidates.length === 0 && (
                <div className="tiny" style={{ color: 'var(--pencil)' }}>
                  예시 루틴을 모두 쓰고 있어요 — 대단한데요!
                </div>
              )}
              {candidates.map((p) => {
                const added = state.routines.some((r) => r.label === p.label);
                return (
                  <div
                    key={p.label}
                    style={{
                      display: 'flex',
                      alignItems: 'center',
                      gap: 10,
                      padding: '8px 10px',
                      border: '1.5px solid var(--ink)',
                      borderRadius: 12,
                      background: 'var(--paper)',
                      opacity: added ? 0.55 : 1,
                    }}
                  >
                    <span style={{ fontSize: 18 }} aria-hidden="true">{p.emoji}</span>
                    <span style={{ flex: 1, fontFamily: 'Pretendard', fontWeight: 600 }}>{p.label}</span>
                    <span className="tiny" style={{ color: 'var(--pencil)' }}>{CATEGORY_LABEL[p.category]}</span>
                    {added ? (
                      <span className="chip">진행중</span>
                    ) : (
                      <button
                        type="button"
                        onClick={() => {
                          dispatch({ type: 'routine/add', label: p.label, emoji: p.emoji, category: p.category });
                          flash(`홈 데일리 체크에 추가됐어요 — ${p.label}`);
                        }}
                        className="chip chip-btn ink"
                        style={{ cursor: 'pointer', fontFamily: 'inherit' }}
                      >
                        + 추가
                      </button>
                    )}
                  </div>
                );
              })}
            </div>
          </div>

          {/* 주중 추가 분석 = 프리미엄 */}
          <button
            type="button"
            className="hbox dashed as-button"
            onClick={() => flash('한 주에 여러 번 인사이트는 프리미엄에서 준비 중이에요 🔒')}
            style={{
              padding: 12,
              marginTop: 10,
              display: 'flex',
              alignItems: 'center',
              gap: 10,
              width: '100%',
              textAlign: 'left',
              cursor: 'pointer',
              background: 'transparent',
            }}
          >
            <div className="ph-circle" style={{ width: 36, height: 36, flex: 'none' }}>🔒</div>
            <div style={{ flex: 1 }}>
              <div style={{ fontFamily: 'Pretendard', fontWeight: 700 }}>지금 다시 분석하기</div>
              <div className="tiny" style={{ color: 'var(--pencil)' }}>주 1회는 무료 — 더 자주 보고 싶다면 프리미엄</div>
            </div>
          </button>
        </>
      )}

      <button
        type="button"
        className="hbox r-r as-button"
        onClick={() => nav.go('report')}
        aria-label="주간 리포트 열기"
        style={{
          padding: 12,
          marginTop: 12,
          display: 'flex',
          alignItems: 'center',
          gap: 10,
          cursor: 'pointer',
        }}
      >
        <div className="ph-circle" style={{ width: 36, height: 36, flex: 'none' }}>
          ◇
        </div>
        <div style={{ flex: 1 }}>
          <div style={{ fontWeight: 700 }}>이번 주 리포트 보기</div>
          <div className="tiny">매주 일요일 발행 · 한 주 요약 카드</div>
        </div>
        <span style={{ fontSize: 22 }}>›</span>
      </button>
    </div>
    {toast && <div className="toast" role="status">{toast}</div>}
    <TabBar active="ins" />
  </div>
  );
};
