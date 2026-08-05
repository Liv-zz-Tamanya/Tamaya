import { useRef, useState } from 'react';
import { BackButton, CatSketch, MoodFace, TabBar, useToast } from '../components/primitives';
import { useNav } from '../lib/router';
import {
  CATEGORIES,
  CATEGORY_LABEL,
  MOOD_LABEL,
  ROUTINE_EMOJIS,
  ROUTINE_PRESETS,
  WEEKDAY_KR,
  dayLogFor,
  groupByCategory,
  isWithinLastWeek,
  latestEntry,
  useStore,
} from '../lib/store';
import type { Category, Routine } from '../lib/store';
import { HEALTH_SURVEY_URL, openSurvey } from '../lib/surveys';
import { formatKoreanTime, getTimeUntilNextOpen } from '../lib/nightChat';

// 06-08 · Home Day / Home Night / Day Log(낮 기록: 루틴 체크 + 메모)
// 낮엔 이음이가 자므로 대화 없음 — 기록형만. (낮 채팅은 프리미엄 예정)

const inputStyle = {
  flex: 1,
  minWidth: 0,
  border: '1.5px solid var(--ink)',
  borderRadius: 999,
  padding: '9px 14px',
  background: 'var(--paper)',
  fontFamily: 'Pretendard',
  fontSize: 16, /* iOS Safari 자동 줌 방지 */
  color: 'var(--ink)',
  outline: 'none',
} as const;

// 카테고리 선택 칩 — 루틴 추가/수정·메모 태그가 같은 어휘를 쓴다.
const CategoryChips = ({
  value,
  onChange,
  label,
}: {
  value: Category;
  onChange: (c: Category) => void;
  label: string;
}) => (
  <div role="group" aria-label={label} style={{ display: 'flex', gap: 6, flexWrap: 'wrap' }}>
    {CATEGORIES.map((c) => (
      <button
        key={c}
        type="button"
        onClick={() => onChange(c)}
        className={'chip chip-btn ' + (value === c ? 'solid' : 'dashed')}
        aria-pressed={value === c}
        style={{ cursor: 'pointer', fontFamily: 'inherit', background: value === c ? undefined : 'transparent' }}
      >
        {CATEGORY_LABEL[c]}
      </button>
    ))}
  </div>
);

const EmojiChips = ({ value, onChange }: { value: string; onChange: (e: string) => void }) => (
  <div role="group" aria-label="이모지 고르기" style={{ display: 'flex', gap: 4, flexWrap: 'wrap' }}>
    {ROUTINE_EMOJIS.map((e) => (
      <button
        key={e}
        type="button"
        onClick={() => onChange(e)}
        aria-pressed={value === e}
        aria-label={`이모지 ${e}`}
        className="as-button"
        style={{
          width: 32,
          height: 32,
          fontSize: 17,
          lineHeight: '30px',
          textAlign: 'center',
          borderRadius: 10,
          cursor: 'pointer',
          border: '1.5px solid var(--ink)',
          background: value === e ? 'var(--accent-soft)' : 'var(--paper)',
        }}
      >
        {e}
      </button>
    ))}
  </div>
);

// 카테고리 섹션 헤더 — 라벨 칩 + 우측 카운트. 낮 홈·밤 홈·낮 기록이 같은 모양을 공유한다.
const CategoryHeader = ({ label, count }: { label: string; count: string }) => (
  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
    <span className="chip" style={{ fontWeight: 700 }}>
      {label}
    </span>
    <span className="tiny" style={{ color: 'var(--pencil)' }}>
      {count}
    </span>
  </div>
);

export const S06_HomeDay = ({ night = false }: { night?: boolean }) => {
  const nav = useNav();
  const { state, dispatch } = useStore();
  const { toast, flash } = useToast();
  // 카테고리별 가로 스크롤이 여러 개지만 마우스 드래그는 한 번에 하나뿐 → ref 하나 공유.
  const routineDragRef = useRef({ active: false, startX: 0, startScroll: 0, didDrag: false });
  const minutesUntilOpen = getTimeUntilNextOpen(nav.now, nav.nightOpenTime);
  const remaining = `${Math.floor(minutesUntilOpen / 60)}시간 ${minutesUntilOpen % 60}분`;
  const log = dayLogFor(state.dayLog, nav.now);
  const routines = state.routines;
  const dailyDone = routines.filter((r) => log.checks[r.id]).length;
  // 낮·밤 홈 공용 4 카테고리 그룹 (건강→학습→자격증→취미). 합계·포인트는 전 카테고리 합산 유지.
  const routineGroups = groupByCategory(routines);
  const memoGroups = groupByCategory(log.memos);
  // 로컬 store 실값 바인딩(서버 미전송, (C)경계 = 온디바이스 유지) + 빈상태.
  const latest = latestEntry(state.diaries);
  // v4 S06: 카드 수치는 텍스트만(이모지 없음) — "N / 7 일" · "N pt" · "옷장" 표기
  const cond = latest ? MOOD_LABEL[latest.moods[0]] : '기록 전';
  const weekCount = state.diaries.filter((e) => isWithinLastWeek(e)).length;
  const summary: [string, string, string][] = [
    ['오늘 컨디션', cond, latest ? '최근 회고 기준' : '첫 회고를 해봐요'],
    ['이번 주', `${weekCount} / 7 일`, '함께했어요'],
    ['포인트', `${state.points} pt`, `보상 ${state.unlockedItems.length}개`],
    ['키우기', '준비 중', '의견 주기 ›'],
  ];
  const toggleRoutineFromHome = (routine: Routine) => {
    if (routineDragRef.current.didDrag) {
      routineDragRef.current.didDrag = false;
      return;
    }
    const wasDone = !!log.checks[routine.id];
    dispatch({ type: 'routine/toggle', id: routine.id });
    if (!wasDone) {
      dispatch({ type: 'points/add', delta: 10 });
      flash(`+10 ◉  ${routine.label}`);
    }
  };
  return (
  <div className="screen">
    <div className="screen-scroll" style={{ padding: 'calc(46px + var(--safe-t)) 18px calc(88px + var(--safe-b, 0px))' }}>
      <div
        style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'flex-start',
          marginBottom: 12,
        }}
      >
        {/* v4 S06: 제목 먼저, 날짜는 아래 — 한 줄 인사 */}
        <div>
          <h1 className="h-title">좋은 {night ? '밤' : '아침'}, {state.character.name || '친구'}</h1>
          <div className="tiny" style={{ marginTop: 4 }}>{nav.now.getMonth() + 1}월 {nav.now.getDate()}일 · {WEEKDAY_KR[nav.now.getDay()]}요일</div>
        </div>
        <div
          style={{ display: 'flex', flexDirection: 'column', gap: 4, alignItems: 'flex-end' }}
        >
          <button
            type="button"
            onClick={() => nav.go('settings')}
            className="chip"
            aria-label="설정"
            style={{ cursor: 'pointer', fontFamily: 'inherit' }}
          >
            ⚙
          </button>
          <span className="chip">Lv.{state.level}</span>
          <span className="chip">🔥 {state.streak}일</span>
        </div>
      </div>

      {night ? (
        <div
          className="hbox night r-l"
          style={{ padding: 16, marginTop: 6, height: 168, boxSizing: 'border-box', position: 'relative', overflow: 'visible', borderColor: 'var(--accent-soft)' }}
        >
          <svg width="100%" height="40" viewBox="0 0 375 40" preserveAspectRatio="xMidYMid slice" style={{ position: 'absolute', top: 6, left: 0, opacity: 0.4 }}>
            {[[40, 12], [120, 24], [260, 16], [320, 30]].map(([x, y], i) => (
              <circle key={i} cx={x} cy={y} r="1.2" fill="var(--paper)" />
            ))}
          </svg>
          <h2 className="h-section" style={{ color: 'var(--accent-soft)' }}>저녁 회고 · 매일 밤</h2>
          <div className="h-title" style={{ color: 'var(--paper)', marginTop: 2, fontSize: 22 }}>
            "오늘 하루, 잠깐 돌아볼까?"
          </div>
          <div style={{ position: 'absolute', left: 2, bottom: -24, zIndex: 1, lineHeight: 0 }}>
            <MoodFace mood={'\u{1F60C}'} size={150} />
          </div>
          <button
            type="button"
            onClick={() => nav.go('recap-start')}
            className="btn primary"
            style={{ position: 'absolute', right: 16, bottom: 18, cursor: 'pointer', fontFamily: 'inherit' }}
          >
            시작하기 →
          </button>
        </div>
      ) : (
        <div className="hbox day r-l" style={{ padding: 16, marginTop: 6 }}>
          <h2 className="h-section" style={{ color: 'var(--accent)' }}>이음이는 자는 중</h2>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 0, marginTop: 4 }}>
            <div style={{ flex: 1 }}>
              <div style={{ fontFamily: 'Pretendard', fontWeight: 700, marginTop: 2 }}>깨어나기까지 남은 시간</div>
              <div className="h-title" style={{ marginTop: 2, fontSize: 26 }}>{remaining}</div>
            </div>
            <div style={{ width: 150, height: 80, marginRight: -12, marginTop: -8, display: 'flex', alignItems: 'center', justifyContent: 'flex-end', flex: 'none', overflow: 'visible' }}>
              <div style={{ transform: 'translateY(-8px)' }}>
                <CatSketch sleeping size={150} />
              </div>
            </div>
          </div>
          <div className="bar" style={{ marginTop: 12, background: 'var(--paper-2)' }}>
            <i style={{ width: '55%', background: 'var(--ink)', borderRightColor: 'var(--ink)' }} />
          </div>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginTop: 10 }}>
            <div className="tiny">오늘 밤 {formatKoreanTime(nav.nightOpenTime)}에 깨어나요</div>
            <button type="button" onClick={() => nav.wakeNightChat()} className="btn" style={{ cursor: 'pointer', fontFamily: 'inherit' }}>
              이음이 깨우기
            </button>
          </div>
        </div>
      )}

      <section
        className="hbox r-r"
        aria-label={`오늘의 루틴, ${dailyDone} / ${routines.length} 완료`}
        style={{ padding: 14, marginTop: 12 }}
      >
        <div
          style={{
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
            marginBottom: 8,
          }}
        >
          <div className="h-section">오늘의 루틴</div>
          <span className="tiny">{dailyDone} / {routines.length}</span>
        </div>
        {routines.length === 0 && (
          <div className="tiny" style={{ color: 'var(--pencil)' }}>
            아직 루틴이 없어요 — 아래 [오늘 기록하기]에서 하나 골라봐요
          </div>
        )}
        {/* 건강→학습→자격증→취미 4 카테고리 (빈 카테고리는 접힘) — 낮·밤 홈 공통 */}
        {routineGroups.map((group) => {
          if (group.items.length === 0) return null;
          const groupDone = group.items.filter((r) => log.checks[r.id]).length;
          return (
            <div key={group.category} style={{ marginTop: 8 }}>
              <CategoryHeader label={group.label} count={`${groupDone} / ${group.items.length}`} />
              <div
                aria-label={`${group.label} 루틴 목록`}
                className="routine-scroll"
                onMouseDown={(event) => {
                  const el = event.currentTarget;
                  routineDragRef.current = { active: true, startX: event.clientX, startScroll: el.scrollLeft, didDrag: false };
                  el.style.cursor = 'grabbing';
                }}
                onMouseMove={(event) => {
                  const drag = routineDragRef.current;
                  const el = event.currentTarget;
                  if (!drag.active) return;
                  const delta = event.clientX - drag.startX;
                  if (Math.abs(delta) > 4) drag.didDrag = true;
                  el.scrollLeft = drag.startScroll - delta;
                }}
                onMouseUp={(event) => {
                  routineDragRef.current.active = false;
                  event.currentTarget.style.cursor = 'grab';
                }}
                onMouseLeave={(event) => {
                  routineDragRef.current.active = false;
                  event.currentTarget.style.cursor = 'grab';
                }}
                style={{ display: 'flex', gap: 6, overflowX: 'auto', scrollSnapType: 'x proximity', cursor: 'grab', userSelect: 'none', marginTop: 6 }}
              >
                {group.items.map((r) => {
                  const on = !!log.checks[r.id];
                  return (
                    <button
                      key={r.id}
                      type="button"
                      onClick={() => toggleRoutineFromHome(r)}
                      aria-pressed={on}
                      aria-label={`${group.label} · ${r.label} ${on ? '완료' : '미완료'}`}
                      className="as-button"
                      style={{ flex: '0 0 62px', scrollSnapAlign: 'start', textAlign: 'center', cursor: 'pointer', fontFamily: 'inherit' }}
                    >
                      <div
                        style={{
                          width: 44,
                          height: 44,
                          margin: '0 auto',
                          display: 'flex',
                          alignItems: 'center',
                          justifyContent: 'center',
                          borderRadius: 14,
                          border: '0.5px solid var(--ink)',
                          background: on ? 'var(--ink)' : 'var(--paper)',
                          fontSize: 20,
                        }}
                      >
                        {r.emoji}
                      </div>
                      <div
                        className="tiny"
                        style={{
                          marginTop: 4,
                          overflow: 'hidden',
                          whiteSpace: 'nowrap',
                          textOverflow: 'ellipsis',
                        }}
                      >
                        {r.label}
                      </div>
                    </button>
                  );
                })}
              </div>
            </div>
          );
        })}
      </section>

      {/* 오늘의 메모(행동) — 루틴과 같은 4 카테고리로. 낮·밤 홈 공통, 없으면 섹션 자체가 없음 */}
      {log.memos.length > 0 && (
        <section
          className="hbox r-l"
          aria-label={`오늘의 메모 ${log.memos.length}건`}
          style={{ padding: 14, marginTop: 12 }}
        >
          <div
            style={{
              display: 'flex',
              justifyContent: 'space-between',
              alignItems: 'center',
              marginBottom: 4,
            }}
          >
            <div className="h-section">오늘의 메모</div>
            <span className="tiny">{log.memos.length}건</span>
          </div>
          {memoGroups.map((group) => {
            if (group.items.length === 0) return null;
            return (
              <div key={group.category} style={{ marginTop: 8 }}>
                <CategoryHeader label={group.label} count={`${group.items.length}건`} />
                <div style={{ display: 'flex', flexDirection: 'column', gap: 4, marginTop: 6 }}>
                  {group.items.map((m) => (
                    <div key={m.id} style={{ display: 'flex', gap: 6 }}>
                      <span className="tiny" style={{ color: 'var(--pencil)', flex: 'none' }} aria-hidden="true">
                        ·
                      </span>
                      <span className="body" style={{ flex: 1, minWidth: 0, overflowWrap: 'anywhere' }}>
                        {m.text}
                      </span>
                    </div>
                  ))}
                </div>
              </div>
            );
          })}
        </section>
      )}

      <button
        type="button"
        className="hbox r-l as-button"
        onClick={() => nav.go('daily-check')}
        aria-label="오늘 기록하기 — 루틴 전체 관리와 한 줄 메모"
        style={{
          padding: 14,
          marginTop: 12,
          display: 'flex',
          alignItems: 'center',
          gap: 12,
          cursor: 'pointer',
          background: 'var(--banner)',
          color: 'var(--ink)',
          width: '100%',
          textAlign: 'left',
        }}
      >
        <div className="ph-circle" style={{ width: 40, height: 40, background: 'var(--night)', color: 'var(--cream)' }}>
          ✎
        </div>
        <div style={{ flex: 1 }}>
          <div style={{ fontFamily: 'Pretendard', fontWeight: 700, color: 'var(--ink)' }}>
            오늘 기록하기
          </div>
          <div className="tiny" style={{ color: 'var(--ink-soft)' }}>루틴 체크 + 한 줄 메모 — 밤 회고 재료가 돼요</div>
        </div>
        <span className="handwriting" style={{ fontSize: 24, color: 'var(--ink)' }} aria-hidden="true">
          ›
        </span>
      </button>

      <div
        style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 10, marginTop: 12 }}
      >
        {summary.map(([t, big, sub], i) => {
          const clickable = i === 3;
          const cardClass = 'hbox r-' + (i % 2 ? 'l' : 'r') + (clickable ? ' as-button' : '');
          const cardStyle = {
            padding: 12,
            cursor: clickable ? 'pointer' : 'default',
            position: 'relative' as const,
            ...(clickable ? { display: 'block' as const, width: '100%', textAlign: 'left' as const } : {}),
          };
          const content = (
            <>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                <div className="tiny">{t}</div>
                {i === 3 && state.unlockedItems.length > 0 && (
                  <span
                    className="tiny"
                    style={{
                      background: 'var(--accent-soft)',
                      color: 'var(--ink)',
                      borderRadius: 999,
                      padding: '1px 7px',
                      fontWeight: 700,
                      letterSpacing: 0,
                    }}
                  >
                    NEW!
                  </span>
                )}
              </div>
              <div className="h-title" style={{ fontSize: 18, marginTop: 2 }}>
                {big}
              </div>
              <div className="tiny" style={{ marginTop: 2 }}>
                {sub}
              </div>
            </>
          );
          return clickable ? (
            <button
              key={i}
              type="button"
              className={cardClass}
              onClick={() => nav.go('cat-room')}
              aria-label={`${t} — ${big}, 보러가기`}
              style={cardStyle}
            >
              {content}
            </button>
          ) : (
            <div key={i} className={cardClass} style={cardStyle}>
              {content}
            </div>
          );
        })}
      </div>

      {/* 건강 기록 — 출시 예정 티저 (프리미엄 전용 예정, 탭하면 설문 새 창) */}
      <button
        type="button"
        className="hbox night r-l as-button"
        onClick={() => {
          if (!openSurvey(HEALTH_SURVEY_URL)) {
            flash('설문 링크를 준비 중이에요 — 조금만 기다려줘요');
          }
        }}
        aria-label="건강 기록 출시 예정 — 설문으로 의견 남기기"
        style={{
          padding: 14,
          marginTop: 12,
          display: 'flex',
          alignItems: 'center',
          gap: 12,
          cursor: 'pointer',
          width: '100%',
          textAlign: 'left',
          color: 'var(--paper)',
        }}
      >
        <div className="ph-circle" style={{ width: 40, height: 40, background: 'var(--paper)', color: 'var(--ink)', flex: 'none' }}>
          ♥
        </div>
        <div style={{ flex: 1, minWidth: 0 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
            <span style={{ fontFamily: 'Pretendard', fontWeight: 700 }}>건강 기록</span>
            <span
              className="tiny"
              style={{
                background: 'var(--accent-soft)',
                color: 'var(--ink)',
                borderRadius: 999,
                padding: '1px 7px',
                fontWeight: 700,
                letterSpacing: 0,
              }}
            >
              출시 예정
            </span>
          </div>
          <div className="tiny" style={{ color: 'var(--accent-soft)', marginTop: 2 }}>
            수면·걸음까지 한 곳에 — 프리미엄으로 준비 중, 의견을 들려주세요 ↗
          </div>
        </div>
        <span className="handwriting" style={{ fontSize: 24 }} aria-hidden="true">›</span>
      </button>
    </div>
    {toast && <div className="toast" role="status">{toast}</div>}
    <TabBar active="home" />
  </div>
  );
};

export const S07_HomeNight = () => <S06_HomeDay night />;

export const S08_DayLog = () => {
  const nav = useNav();
  const { state, dispatch } = useStore();
  const { toast, flash } = useToast();
  const [manage, setManage] = useState(false);
  const [newLabel, setNewLabel] = useState('');
  const [newCat, setNewCat] = useState<Category>(state.interests[0] ?? 'health');
  const [newEmoji, setNewEmoji] = useState('☑️');
  // 인라인 수정 — 편집 중인 루틴 1건만 폼으로 바뀐다.
  const [editingId, setEditingId] = useState<string | null>(null);
  const [editLabel, setEditLabel] = useState('');
  const [editEmoji, setEditEmoji] = useState('☑️');
  const [editCat, setEditCat] = useState<Category>('health');
  const [memoText, setMemoText] = useState('');
  const [memoCat, setMemoCat] = useState<Category>(state.interests[0] ?? 'health');

  const log = dayLogFor(state.dayLog, nav.now);
  const routines = state.routines;
  // 완료·포인트 카운터는 카테고리와 무관한 전체 합산 (그룹핑 전과 동일).
  const doneCount = routines.filter((r) => log.checks[r.id]).length;
  // 기록된 한 줄 메모도 루틴과 같은 4 카테고리 순서로 묶어 보여준다.
  const memoGroups = groupByCategory(log.memos);

  const toggle = (r: Routine) => {
    const was = !!log.checks[r.id];
    dispatch({ type: 'routine/toggle', id: r.id });
    if (!was) {
      dispatch({ type: 'points/add', delta: 10 });
      flash(`+10 ◉  ${r.label}`);
    }
  };

  const addRoutine = (label: string, emoji?: string) => {
    const trimmed = label.trim();
    if (!trimmed) return;
    if (routines.some((r) => r.label === trimmed)) {
      flash('이미 같은 이름의 루틴이 있어요');
      return;
    }
    dispatch({ type: 'routine/add', label: trimmed, emoji: emoji ?? newEmoji, category: newCat });
    setNewLabel('');
  };

  const startEdit = (r: Routine) => {
    setEditingId(r.id);
    setEditLabel(r.label);
    setEditEmoji(r.emoji);
    setEditCat(r.category);
  };

  const saveEdit = () => {
    if (!editingId) return;
    const label = editLabel.trim();
    if (!label) return;
    if (routines.some((r) => r.id !== editingId && r.label === label)) {
      flash('이미 같은 이름의 루틴이 있어요');
      return;
    }
    dispatch({ type: 'routine/update', id: editingId, label, emoji: editEmoji, category: editCat });
    setEditingId(null);
  };

  const addMemo = () => {
    const text = memoText.trim();
    if (!text) return;
    dispatch({ type: 'memo/add', text, category: memoCat });
    setMemoText('');
  };

  // 현재 카테고리에서 아직 추가 안 한 예시 루틴 제안
  const suggestions = ROUTINE_PRESETS[newCat]
    .filter((p) => !routines.some((r) => r.label === p.label))
    .slice(0, 3);

  return (
  <div className="screen">
    <div className="screen-scroll" style={{ padding: 'calc(46px + var(--safe-t)) 18px calc(88px + var(--safe-b, 0px))' }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 6 }}>
        <BackButton onClick={() => nav.back()} />
        <h1 className="h-title" style={{ fontSize: 22 }}>낮 기록</h1>
      </div>
      <div className="tiny">루틴 체크 + 한 줄 메모 — 밤 회고 때 이음이가 함께 봐요</div>

      <div style={{ display: 'flex', gap: 6, marginTop: 14 }}>
        {routines.map((r) => (
          <div
            key={r.id}
            style={{
              flex: 1,
              height: 6,
              borderRadius: 999,
              border: '1.5px solid var(--ink)',
              background: log.checks[r.id] ? 'var(--night)' : 'var(--paper)',
            }}
          />
        ))}
      </div>
      <div className="tiny" style={{ marginTop: 6 }}>
        {doneCount} / {routines.length} 완료 · 오늘 +{state.points} 포인트 ◉
      </div>

      {routines.length > 0 && doneCount === routines.length && (
        <div className="hbox accent r-r" style={{ padding: 12, marginTop: 10, textAlign: 'center' }}>
          <div style={{ fontFamily: 'Pretendard', fontWeight: 700 }}>🎉 오늘 루틴 모두 완료!</div>
          <div className="tiny" style={{ marginTop: 2 }}>꾸준함이 이음이를 키워요</div>
        </div>
      )}

      {/* 루틴 투두리스트 — 건강·학습·자격증·취미 4 섹션 (완료 카운터는 전체 합산) */}
      <div className="hbox r-l" style={{ padding: 14, marginTop: 14 }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <h2 className="h-label">오늘의 루틴</h2>
          <button
            type="button"
            onClick={() => {
              setManage((m) => !m);
              setEditingId(null);
            }}
            className={'chip chip-btn ' + (manage ? 'solid' : '')}
            aria-pressed={manage}
            style={{ cursor: 'pointer', fontFamily: 'inherit' }}
          >
            {manage ? '완료' : '관리'}
          </button>
        </div>
        {routines.length === 0 && (
          <div className="tiny" style={{ color: 'var(--pencil)', marginTop: 10 }}>
            아직 루틴이 없어요 — [관리]에서 하나 골라봐요
          </div>
        )}

        {CATEGORIES.map((cat) => {
          const items = routines.filter((r) => r.category === cat);
          if (items.length === 0 && !manage) return null;
          const catDone = items.filter((r) => log.checks[r.id]).length;
          return (
            <section
              key={cat}
              aria-label={`${CATEGORY_LABEL[cat]} 루틴 ${catDone} / ${items.length}`}
              style={{ marginTop: 12 }}
            >
              <CategoryHeader label={CATEGORY_LABEL[cat]} count={`${catDone} / ${items.length}`} />
              <div style={{ display: 'flex', flexDirection: 'column', gap: 8, marginTop: 8 }}>
                {items.length === 0 && (
                  <div className="tiny" style={{ color: 'var(--pencil)' }}>
                    여긴 아직 비어 있어요 — 원하면 아래에서 하나 추가해요
                  </div>
                )}
                {items.map((r) => {
                  const on = !!log.checks[r.id];
                  if (editingId === r.id)
                    return (
                      <form
                        key={r.id}
                        onSubmit={(e) => {
                          e.preventDefault();
                          saveEdit();
                        }}
                        aria-label={`${r.label} 수정`}
                        style={{
                          padding: 10,
                          border: '1.5px solid var(--ink)',
                          borderRadius: 12,
                          background: 'var(--paper-2)',
                          display: 'flex',
                          flexDirection: 'column',
                          gap: 8,
                        }}
                      >
                        <CategoryChips value={editCat} onChange={setEditCat} label="루틴 카테고리 수정" />
                        <EmojiChips value={editEmoji} onChange={setEditEmoji} />
                        <div style={{ display: 'flex', gap: 8 }}>
                          <input
                            value={editLabel}
                            onChange={(e) => setEditLabel(e.target.value)}
                            maxLength={20}
                            aria-label="루틴 이름 수정"
                            style={inputStyle}
                            autoFocus
                          />
                          <button type="submit" className="btn" style={{ cursor: 'pointer', fontFamily: 'inherit' }}>
                            저장
                          </button>
                          <button
                            type="button"
                            onClick={() => setEditingId(null)}
                            className="chip chip-btn"
                            style={{ cursor: 'pointer', fontFamily: 'inherit' }}
                          >
                            취소
                          </button>
                        </div>
                      </form>
                    );
                  return (
                        <div key={r.id} style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                          <button
                            type="button"
                            onClick={() => toggle(r)}
                            aria-pressed={on}
                            aria-label={`${r.label} ${on ? '완료됨' : '체크하기'}`}
                            className="as-button"
                            style={{
                              flex: 1,
                              minWidth: 0,
                              display: 'flex',
                              alignItems: 'center',
                              gap: 10,
                              padding: '8px 10px',
                              border: '1.5px solid var(--ink)',
                              borderRadius: 12,
                              background: on ? 'var(--paper-2)' : 'var(--paper)',
                              cursor: 'pointer',
                              textAlign: 'left',
                            }}
                          >
                            <div className={'check sq ' + (on ? 'on' : '')} style={{ width: 22, height: 22 }}>
                              {on ? '✓' : ''}
                            </div>
                            <span style={{ fontSize: 18 }} aria-hidden="true">{r.emoji}</span>
                            <span
                              style={{
                                flex: 1,
                                minWidth: 0,
                                fontFamily: 'Pretendard',
                                fontWeight: 600,
                                textDecoration: on ? 'line-through' : 'none',
                                opacity: on ? 0.6 : 1,
                              }}
                            >
                              {r.label}
                            </span>
                          </button>
                          {manage && (
                            <>
                              <button
                                type="button"
                                onClick={() => startEdit(r)}
                                aria-label={`${r.label} 수정`}
                                className="chip chip-btn"
                                style={{ cursor: 'pointer', fontFamily: 'inherit' }}
                              >
                                ✎
                              </button>
                              <button
                                type="button"
                                onClick={() => dispatch({ type: 'routine/remove', id: r.id })}
                                aria-label={`${r.label} 삭제`}
                                className="chip chip-btn"
                                style={{ cursor: 'pointer', fontFamily: 'inherit' }}
                              >
                                ✕
                              </button>
                            </>
                          )}
                        </div>
                  );
                })}
              </div>
            </section>
          );
        })}

        {manage && (
          <div style={{ marginTop: 14, borderTop: '1.5px dashed var(--muted)', paddingTop: 12 }}>
            <div className="tiny" style={{ marginBottom: 6 }}>새 루틴 추가</div>
            <div style={{ marginBottom: 8 }}>
              <CategoryChips value={newCat} onChange={setNewCat} label="새 루틴 카테고리" />
            </div>
            <div style={{ marginBottom: 8 }}>
              <EmojiChips value={newEmoji} onChange={setNewEmoji} />
            </div>
            <form
              onSubmit={(e) => {
                e.preventDefault();
                addRoutine(newLabel);
              }}
              style={{ display: 'flex', gap: 8 }}
            >
              <input
                value={newLabel}
                onChange={(e) => setNewLabel(e.target.value)}
                maxLength={20}
                placeholder="예: 저녁 10분 산책"
                aria-label="새 루틴 이름"
                style={inputStyle}
              />
              <button type="submit" className="btn" style={{ cursor: 'pointer', fontFamily: 'inherit' }}>
                추가
              </button>
            </form>
            {suggestions.length > 0 && (
              <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap', marginTop: 8 }}>
                {suggestions.map((p) => (
                  <button
                    key={p.label}
                    type="button"
                    onClick={() => addRoutine(p.label, p.emoji)}
                    className="chip chip-btn dashed"
                    style={{ cursor: 'pointer', fontFamily: 'inherit', background: 'transparent' }}
                  >
                    + {p.emoji} {p.label}
                  </button>
                ))}
              </div>
            )}
          </div>
        )}
      </div>

      {/* 한 줄 메모장 — 태그는 루틴 카테고리와 같은 4분류 어휘 */}
      <div className="hbox r-r" style={{ padding: 14, marginTop: 10 }}>
        <h2 className="h-label">한 줄 메모</h2>
        <div className="tiny" style={{ marginTop: 2 }}>오늘 있었던 일을 태그와 함께 짧게 — 밤에 같이 정리해요</div>
        <div style={{ marginTop: 10 }}>
          <CategoryChips value={memoCat} onChange={setMemoCat} label="메모 태그" />
        </div>
        <form
          onSubmit={(e) => {
            e.preventDefault();
            addMemo();
          }}
          style={{ display: 'flex', gap: 8, marginTop: 8 }}
        >
          <input
            value={memoText}
            onChange={(e) => setMemoText(e.target.value)}
            maxLength={60}
            placeholder={`${CATEGORY_LABEL[memoCat]}에 남길 한 줄...`}
            aria-label="한 줄 메모"
            style={inputStyle}
          />
          <button type="submit" className="btn" style={{ cursor: 'pointer', fontFamily: 'inherit' }}>
            남기기
          </button>
        </form>
        {/* 기록된 메모도 루틴과 같은 4 카테고리 섹션 (빈 카테고리는 접힘 — 루틴 리스트와 동일 규칙) */}
        {memoGroups.map((group) => {
          if (group.items.length === 0) return null;
          return (
            <section
              key={group.category}
              aria-label={`${group.label} 메모 ${group.items.length}건`}
              style={{ marginTop: 12 }}
            >
              <CategoryHeader label={group.label} count={`${group.items.length}건`} />
              <div style={{ display: 'flex', flexDirection: 'column', gap: 6, marginTop: 8 }}>
                {group.items.map((m) => (
                  <div key={m.id} style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                    <span className="tiny" style={{ color: 'var(--pencil)', flex: 'none' }} aria-hidden="true">
                      ·
                    </span>
                    <span className="body" style={{ flex: 1, minWidth: 0, overflowWrap: 'anywhere' }}>{m.text}</span>
                    <button
                      type="button"
                      onClick={() => dispatch({ type: 'memo/remove', id: m.id })}
                      aria-label={`${group.label} 메모 삭제`}
                      className="tiny as-button"
                      style={{ cursor: 'pointer', color: 'var(--pencil)', background: 'none', border: 'none' }}
                    >
                      ✕
                    </button>
                  </div>
                ))}
              </div>
            </section>
          );
        })}
      </div>

      {/* 낮 대화는 프리미엄 예정 — 잠금 티저 (이음이는 자는 중) */}
      <button
        type="button"
        className="hbox dashed as-button"
        onClick={() => flash('이음이와 낮 대화는 프리미엄에서 준비 중이에요 🔒')}
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
          <div style={{ fontFamily: 'Pretendard', fontWeight: 700 }}>이음이와 낮 대화</div>
          <div className="tiny" style={{ color: 'var(--pencil)' }}>프리미엄 · 준비 중 — 지금은 이음이가 자는 시간이에요</div>
        </div>
      </button>
    </div>
    {toast && <div className="toast" role="status">{toast}</div>}
    <TabBar active="home" />
  </div>
  );
};
