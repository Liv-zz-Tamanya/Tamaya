import { useEffect, useRef, useState } from 'react';
import { BackButton, TabBar } from '../components/primitives';
import { MoodHeatmap } from '../components/mood-heatmap';
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
  dateParts,
  diaryDateOf,
  entriesForMonth,
  entryForDate,
  entryForDay,
  formatDateKey,
  formatMonthDay,
  latestEntry,
  moodByDate,
  statsFor,
  weekdayOfDate,
  useStore,
} from '../lib/store';
import { listDiaries, type DiaryResponse } from '../lib/api';

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
  const [view, setView] = useState<'emoji' | 'heat'>('emoji');
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
  // 히트맵 셀 탭 → 기존 일기 상세 이동 핸들러(openDay) 재사용.
  const openDate = (dateKey: string) => openDay(dateParts(dateKey).day);
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

      {/* 표시 레이어 토글 — 이모지 달력 ↔ 무드 색 히트맵 (서버 조회·월 이동 로직 불변) */}
      <div style={{ display: 'flex', gap: 6, marginTop: 10 }}>
        {(['emoji', 'heat'] as const).map((v) => (
          <button
            key={v}
            type="button"
            onClick={() => setView(v)}
            className={'chip chip-btn ' + (view === v ? 'solid' : '')}
            aria-pressed={view === v}
            style={{ cursor: 'pointer', fontFamily: 'inherit' }}
          >
            {v === 'emoji' ? '이모지' : '무드 색'}
          </button>
        ))}
      </div>

      {view === 'emoji' && (
        <>
      <div
        style={{ display: 'grid', gridTemplateColumns: 'repeat(7, 1fr)', marginTop: 8, gap: 2 }}
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
                  <div
                    style={{
                      width: 30,
                      height: 30,
                      border: today ? '2px solid var(--accent)' : '1.5px solid var(--ink)',
                      borderRadius: '50%',
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                      background: today ? 'var(--paper-2)' : '#fff',
                      fontSize: 14,
                    }}
                  >
                    {mood}
                  </div>
                ) : (
                  <div
                    style={{
                      width: 30,
                      height: 30,
                      border: '1px dashed var(--line)',
                      borderRadius: '50%',
                    }}
                  />
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
        </>
      )}

      {view === 'heat' && (
        <div className="hbox" style={{ marginTop: 8, padding: 12 }}>
          <MoodHeatmap diaries={monthEntries} month={visibleMonth} onSelect={openDate} overlay={localMoods} />
        </div>
      )}

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

      <div
        style={{
          display: 'flex',
          gap: 8,
          marginTop: 12,
          flexWrap: 'wrap',
          justifyContent: 'center',
        }}
      >
        {moodCounts.map((x, i) => (
          <div key={i} className="chip" style={{ background: 'var(--paper)' }}>
            <span>{x.m}</span>
            <span style={{ fontSize: 11, color: 'var(--pencil)' }}>
              {x.label} ×{x.n}
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
              <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginTop: 4 }}>
                <span style={{ fontSize: 20 }}>{recent.moods[0]}</span>
                <span style={{ fontWeight: 700 }}>
                  {recent.moods.map((m) => MOOD_LABEL[m]).join(' · ')}
                </span>
              </div>
            </div>
            <span style={{ fontSize: 22 }}>›</span>
          </div>
          <div className="tiny" style={{ marginTop: 6 }}>
            "{stripDatePrefix(recent).slice(0, 30)}..."
          </div>
        </button>
      )}

      {view === 'emoji' && (
        <div className="tiny" style={{ marginTop: 8, textAlign: 'center', color: 'var(--pencil)' }}>
          ※ 점선 동그라미 = 기록 없음 — 탭해서 빠르게 감정 추가
        </div>
      )}

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
  const checks: [string, boolean][] = [
    ['🍚', !!entry.check.food],
    ['💧', !!entry.check.water],
    ['😴', !!entry.check.sleep],
    ['🚶', !!entry.check.movement],
    ['☼', !!entry.check.sun],
  ];
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
          <span style={{ fontSize: 22 }}>{entry.moods[0]}</span>
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
        <h2 className="h-label">그날의 체크</h2>
        <div
          style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(5, 1fr)',
            gap: 6,
            marginTop: 8,
          }}
        >
          {checks.map(([ic, on], i) => (
            <div key={i} style={{ textAlign: 'center' }}>
              <div
                className="ph-square"
                style={{
                  width: 38,
                  height: 38,
                  margin: '0 auto',
                  background: on ? 'var(--ink)' : 'var(--paper)',
                  color: on ? 'var(--paper)' : 'var(--ink)',
                }}
              >
                {ic}
              </div>
            </div>
          ))}
        </div>
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
  const pct = period === '전체' ? 100 : Math.round((s.writeDays / s.target) * 100);
  const life: [string, string, string][] = [
    ['🍚 식사', `${s.life.food}/${s.writeDays}`, s.life.food >= s.writeDays * 0.7 ? '꾸준 ↑' : '보통'],
    ['😴 수면', `${s.life.sleep}/${s.writeDays}`, s.life.sleep >= s.writeDays * 0.6 ? '양호' : '부족 ↓'],
    ['🚶 운동', `${s.life.movement}/${s.writeDays}`, s.life.movement >= s.writeDays * 0.5 ? '활발' : '보통'],
  ];
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
              {period === '전체' ? '일 누적' : `/ ${s.target} 일`}
            </div>
            <div className="tiny squiggle">
              {period === '주'
                ? `이번 주 ${pct}% 작성`
                : period === '월'
                  ? `5월 ${pct}% 작성`
                  : `누적 기록 ${s.count}건`}
            </div>
          </div>
        </div>
        <div className="bar" style={{ marginTop: 10 }}>
          <i style={{ width: Math.min(100, pct) + '%' }} />
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
                {x.mood} {x.label}
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
        <h2 className="h-label">라이프스타일</h2>
        <div
          style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(3, 1fr)',
            gap: 8,
            marginTop: 8,
          }}
        >
          {life.map(([t, v, sub], i) => (
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

export const S17_Insights = () => {
  const nav = useNav();
  const { state } = useStore();
  const [routine, setRoutine] = useState<null | 'added' | 'later'>(null);
  // 데이터 부족(<5건) 시 인사이트 대신 안내 (feature-spec §F7: 7일 미만 안내).
  const enough = state.diaries.length >= 5;
  return (
  <div className="screen">
    <div className="screen-scroll" style={{ padding: 'calc(46px + var(--safe-t)) 18px calc(88px + var(--safe-b, 0px))' }}>
      <h1 className="h-title">인사이트</h1>
      <div className="tiny" style={{ marginTop: 2 }}>이음이가 정리해준 이번 주</div>

      {enough ? (
        <>
      <div className="hbox night r-l" style={{ padding: 16, marginTop: 14 }}>
        <h2 className="h-label" style={{ color: 'var(--accent-soft)' }}>
          이번 주 메인 패턴
        </h2>
        <div
          className="h-title"
          style={{ color: 'var(--paper)', fontSize: 22, marginTop: 4 }}
        >
          "5분의 틈"이 있던 날엔
          <br />
          피곤이 절반이었어 ⌇
        </div>
        <div
          className="handwriting"
          style={{ color: 'var(--accent-soft)', fontSize: 16, marginTop: 8 }}
        >
          회의 사이 짧은 호흡을 한 화·목요일에는 평온함이
          <br />두 배 많았어요. 같은 패턴, 다음 주에도 ?
        </div>
      </div>

      <h2 className="h-label" style={{ marginTop: 14, marginBottom: 6 }}>
        이번 주 발견
      </h2>
      {/* 발견 카드 — 넓은 폭서 reflow-grid 로 다열 자연 확장(데이터·문구 불변) */}
      <div className="reflow-grid">
      {(
        [
          ['☼', '햇볕 쐰 날 = 잠 더 푹', '3일 중 3일 "푹잠"으로 기록'],
          ['🍜', '따뜻한 점심 → 오후 평온', '우동·죽 먹은 날 피곤 ↓'],
          ['😴', '수면 6h 미만 = 짜증 ↑', '지난 7일 중 2번 발생'],
        ] as [string, string, string][]
      ).map(([ic, t, s], i) => (
        <div
          key={i}
          className={'hbox ' + (i % 2 ? 'r-l' : 'r-r')}
          style={{
            padding: 12,
            display: 'flex',
            alignItems: 'flex-start',
            gap: 10,
          }}
        >
          <div className="ph-circle" style={{ width: 36, height: 36, flex: 'none' }}>
            {ic}
          </div>
          <div style={{ flex: 1 }}>
            <div style={{ fontWeight: 500 }}>{t}</div>
            <div className="tiny" style={{ color: 'var(--pencil)' }}>{s}</div>
          </div>
          <span className="tiny" style={{ color: 'var(--accent)' }}>
            ✦
          </span>
        </div>
      ))}
      </div>

      <div className="hbox accent r-l" style={{ padding: 14, marginTop: 14 }}>
        <h2 className="h-label">이번 주 추천 루틴</h2>
        <div className="h-title" style={{ fontSize: 18, marginTop: 4 }}>
          회의 끝 · 3분 호흡 알람
        </div>
        <div className="tiny" style={{ marginTop: 4 }}>
          패턴 기반 추천 · 알람으로 추가하기
        </div>
        {routine === 'added' ? (
          <div className="tiny" style={{ marginTop: 10, fontWeight: 700 }}>
            ✓ 회의 종료 후 3분 호흡 알람이 추가됐어요
          </div>
        ) : routine === 'later' ? (
          <div className="tiny" style={{ marginTop: 10 }}>
            다음에 다시 추천할게요
          </div>
        ) : (
          <div style={{ display: 'flex', gap: 8, marginTop: 10 }}>
            <button
              type="button"
              onClick={() => setRoutine('later')}
              className="chip chip-btn"
              style={{ background: 'var(--paper)', cursor: 'pointer', fontFamily: 'inherit' }}
            >
              나중에
            </button>
            <button
              type="button"
              onClick={() => setRoutine('added')}
              className="chip chip-btn ink"
              style={{ cursor: 'pointer', fontFamily: 'inherit' }}
            >
              ✓ 추가
            </button>
          </div>
        )}
      </div>
        </>
      ) : (
        <div className="hbox dashed r-l" style={{ padding: 18, marginTop: 14, textAlign: 'center' }}>
          <div className="body">아직 인사이트를 만들 데이터가 적어요</div>
          <div className="tiny" style={{ marginTop: 6 }}>
            회고를 5번 이상 쌓으면 이음이가 패턴을 찾아줘요 (현재 {state.diaries.length}건)
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
          <div className="tiny">매주 월요일 발행 · 한 주 요약 카드</div>
        </div>
        <span style={{ fontSize: 22 }}>›</span>
      </button>

      <div className="sticky" style={{ marginTop: 14, transform: 'rotate(-1.5deg)' }}>
        ※ D7+에 더 깊은 패턴 — 꾸준히 모일수록 정확해져요
      </div>
    </div>
    <TabBar active="ins" />
  </div>
  );
};
