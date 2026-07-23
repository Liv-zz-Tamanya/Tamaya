import { useEffect, useMemo, useRef, useState } from 'react';
import { BackButton, CatSketch, MoodFace, TabBar, useToast } from '../components/primitives';
import { ChatInputRow, ChatThread } from '../components/chat';
import { useNav } from '../lib/router';
import { scrollBehavior } from '../lib/scroll';
import {
  DailyKey,
  MOOD_LABEL,
  WEEKDAY_KR,
  isWithinLastWeek,
  latestEntry,
  simulateAiReply,
  useStore,
} from '../lib/store';
import { AI_ENABLED, sendAiChat } from '../lib/api';
import { formatKoreanTime, getTimeUntilNextOpen } from '../lib/nightChat';

// 06-09 · Home Day / Home Night / Daily Check / AI Chat

export const S06_HomeDay = () => {
  const nav = useNav();
  const { state } = useStore();
  const minutesUntilOpen = getTimeUntilNextOpen(nav.now, nav.nightOpenTime);
  const remaining = `${Math.floor(minutesUntilOpen / 60)}시간 ${minutesUntilOpen % 60}분`;
  const d = state.daily;
  const dailyDone =
    (d.food.done ? 1 : 0) +
    (d.water >= 6 ? 1 : 0) +
    (d.sleep.done ? 1 : 0) +
    (d.movement.done ? 1 : 0) +
    (d.sun.done ? 1 : 0);
  const checks: [string, string, boolean][] = [
    ['🍚', '식사', d.food.done],
    ['💧', '물', d.water >= 6],
    ['😴', '수면', d.sleep.done],
    ['🚶', '운동', d.movement.done],
    ['☼', '햇볕', d.sun.done],
  ];
  // 로컬 store 실값 바인딩(서버 미전송, (C)경계 = 온디바이스 유지) + 빈상태.
  const latest = latestEntry(state.diaries);
  const cond = latest ? `${latest.moods[0]} ${MOOD_LABEL[latest.moods[0]]}` : '😴 기록 전';
  const weekCount = state.diaries.filter((e) => isWithinLastWeek(e)).length;
  const summary: [string, string, string][] = [
    ['오늘 컨디션', cond, latest ? '최근 회고 기준' : '첫 회고를 해봐요'],
    ['이번 주', `${weekCount}일`, '함께했어요'],
    ['포인트', `◉ ${state.points}`, `보상 ${state.unlockedItems.length}개`],
    ['키우기', state.unlockedItems.length ? `아이템 ${state.unlockedItems.length}` : '시작하기', '보러가기 ›'],
  ];
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
        <div>
          <div className="tiny">{nav.now.getMonth() + 1}월 {nav.now.getDate()}일 · {WEEKDAY_KR[nav.now.getDay()]}요일</div>
          <h1 className="h-title" style={{ marginTop: 2 }}>
            좋은 아침,
            <br />
            {state.character.name || '친구'} ☀
          </h1>
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
          <span className="chip">{state.streak}일</span>
        </div>
      </div>

      <div className="hbox day r-l" style={{ padding: 16, marginTop: 6 }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <div>
            <h2 className="h-section" style={{ color: 'var(--accent)' }}>
              이음이는 자는 중
            </h2>
            <div className="tiny" style={{ marginTop: 4 }}>
              깨어나기까지 남은 시간
            </div>
            <div className="h-title" style={{ marginTop: 2, fontSize: 24 }}>
              {remaining}
            </div>
          </div>
          <div className="chip" style={{ background: 'var(--paper)' }}>
            ⏰ {nav.nightOpenTime}
          </div>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 14, marginTop: 10 }}>
          <CatSketch size={86} sleeping />
          <div className="handwriting" style={{ color: 'var(--ink-soft)' }}>
            "쿠울… 쿠울…
            <br />
            이따 만나, 친구"
          </div>
        </div>
        <div className="bar" style={{ marginTop: 12, background: 'var(--paper-2)' }}>
          <i style={{ width: '55%', background: 'var(--ink)', borderRightColor: 'var(--ink)' }} />
        </div>
        <div className="tiny" style={{ marginTop: 4 }}>
          오늘 밤 {formatKoreanTime(nav.nightOpenTime)}에 깨어나요
        </div>
        <button
          type="button"
          onClick={() => nav.wakeNightChat()}
          className="btn"
          style={{ marginTop: 12, cursor: 'pointer', fontFamily: 'inherit' }}
        >
          이음이 깨우기
        </button>
      </div>

      <button
        type="button"
        className="hbox r-r as-button"
        onClick={() => nav.go('daily-check')}
        aria-label={`오늘의 데일리 체크, ${dailyDone} / 5 완료`}
        style={{ padding: 14, marginTop: 12, cursor: 'pointer', display: 'block', width: '100%', textAlign: 'left' }}
      >
        <div
          style={{
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
            marginBottom: 8,
          }}
        >
          <div className="h-section">오늘의 데일리 체크</div>
          <span className="tiny">{dailyDone} / 5</span>
        </div>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(5, 1fr)', gap: 6 }}>
          {checks.map(([ic, l, on], i) => (
            <div key={i} style={{ textAlign: 'center' }}>
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
                  color: on ? 'var(--paper)' : 'var(--ink)',
                }}
              >
                {ic}
              </div>
              <div className="tiny" style={{ marginTop: 4 }}>
                {l}
              </div>
            </div>
          ))}
        </div>
      </button>

      <button
        type="button"
        className="hbox r-l as-button"
        onClick={() => nav.go('ai-chat')}
        aria-label="AI 코칭에게 물어봐요"
        style={{
          padding: 14,
          marginTop: 12,
          display: 'flex',
          alignItems: 'center',
          gap: 12,
          cursor: 'pointer',
          background: 'var(--pencil)',
          color: 'var(--paper)',
          width: '100%',
          textAlign: 'left',
        }}
      >
        <div className="ph-circle" style={{ width: 40, height: 40, background: 'var(--paper)', color: 'var(--ink)' }}>
          ✦
        </div>
        <div style={{ flex: 1 }}>
          <div style={{ fontFamily: 'Pretendard', fontWeight: 700, color: 'var(--paper)' }}>
            AI 코칭에게 물어봐요
          </div>
          <div className="tiny" style={{ color: 'var(--paper)' }}>"점심 뭐 먹지?" "잠이 안 와요"</div>
        </div>
        <span className="handwriting" style={{ fontSize: 24, color: 'var(--paper)' }} aria-hidden="true">
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
    </div>
    <TabBar active="home" />
  </div>
  );
};

export const S07_HomeNight = () => {
  const nav = useNav();
  const { state } = useStore();
  return (
  <div
    className="screen"
    style={{ background: 'var(--night)', color: 'var(--paper)' }}
  >
    <div className="screen-scroll" style={{ padding: 'calc(46px + var(--safe-t)) 18px calc(88px + var(--safe-b, 0px))' }}>
      <div
        style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'flex-start',
          marginBottom: 12,
        }}
      >
        <div>
          <div className="tiny" style={{ color: 'var(--muted)' }}>{nav.now.getMonth() + 1}월 {nav.now.getDate()}일 · {WEEKDAY_KR[nav.now.getDay()]}요일 밤</div>
          <h1 className="h-title" style={{ marginTop: 2, color: 'var(--paper)' }}>
            이음이가
            <br />
            깨어났어요 ☾
          </h1>
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
          <span className="chip">{state.streak}일</span>
        </div>
      </div>

      <div
        className="hbox night r-l"
        style={{ padding: 16, marginTop: 6, position: 'relative', overflow: 'hidden', borderColor: 'var(--accent-soft)' }}
      >
        <svg
          width="100%"
          height="40"
          viewBox="0 0 375 40"
          preserveAspectRatio="xMidYMid slice"
          style={{ position: 'absolute', top: 6, left: 0, opacity: 0.4 }}
        >
          {[
            [40, 12],
            [120, 24],
            [260, 16],
            [320, 30],
          ].map(([x, y], i) => (
            <circle key={i} cx={x} cy={y} r="1.2" fill="var(--paper)" />
          ))}
        </svg>
        <h2 className="h-section" style={{ color: 'var(--accent-soft)' }}>
          저녁 회고 · 매일 밤
        </h2>
        <div className="h-title" style={{ color: 'var(--paper)', marginTop: 2, fontSize: 22 }}>
          "오늘 하루, 잠깐
          <br />
          같이 돌아볼까?"
        </div>
        <div style={{ display: 'flex', alignItems: 'flex-end', gap: 12, marginTop: 14 }}>
          <div
            style={{
              background: 'var(--paper)',
              borderRadius: 12,
              padding: 8,
              border: '1.5px solid var(--ink)',
            }}
          >
            <CatSketch size={70} mood="wink" />
          </div>
          <button
            type="button"
            onClick={() => nav.go('recap-start')}
            className="btn primary"
            style={{ marginLeft: 'auto', cursor: 'pointer', fontFamily: 'inherit' }}
          >
            시작하기 →
          </button>
        </div>
      </div>

      <div
        className="hbox r-r"
        style={{
          padding: 12,
          marginTop: 12,
          display: 'flex',
          alignItems: 'center',
          gap: 12,
        }}
      >
        <div style={{ fontFamily: 'Pretendard', fontWeight: 800, fontSize: 34, color: 'var(--accent)', lineHeight: 1 }}>{state.streak}<span style={{ fontSize: 13, color: 'var(--pencil)', marginLeft: 2 }}>일</span></div>
        <div style={{ flex: 1 }}>
          <div style={{ fontFamily: 'Pretendard', fontWeight: 700 }}>
            {state.streak > 0 ? `${state.streak}일 연속!` : '오늘부터 시작해요'}
          </div>
          <div className="tiny">오늘도 만나서 좋았어</div>
        </div>
        <div style={{ display: 'flex', gap: 3 }}>
          {Array.from({ length: 7 }, (_, i) => (i < Math.min(state.streak, 7) ? 1 : 0)).map((on, i) => (
            <div
              key={i}
              className="ph-circle"
              style={{
                width: 14,
                height: 14,
                background: on ? 'var(--accent-soft)' : '#fff',
                borderColor: 'var(--ink)',
              }}
            />
          ))}
        </div>
      </div>

      <div className="hbox r-l" style={{ padding: 12, marginTop: 12 }}>
        <h2 className="h-section" style={{ marginBottom: 8 }}>
          오늘 미리 표시한 감정
        </h2>
        <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap' }}>
          {(
            [
              ['😌', true],
              ['😊', true],
              ['😣', false],
              ['😢', false],
              ['😡', false],
            ] as [string, boolean][]
          ).map(([e, on], i) => (
            <div
              key={i}
              className={'mood-blob ' + (on ? '' : 'r-l')}
              style={{
                width: 38,
                height: 38,
                background: on ? 'var(--paper-2)' : '#fff',
                opacity: on ? 1 : 0.4,
              }}
            >
              <MoodFace mood={e} size={26} />
            </div>
          ))}
        </div>
        <div className="tiny" style={{ marginTop: 8 }}>
          회고 대화 중 더 정확히 적어줘요
        </div>
      </div>

      <div style={{ marginTop: 12 }}>
        {(
          [
            ['◰', '캘린더', '지난 일기 보기', 'calendar'],
            ['◖', '이음이 방', '꾸미고 먹이주기', 'cat-room'],
            ['✦', '이번 주 인사이트', 'AI 분석', 'insights'],
          ] as [string, string, string, 'calendar' | 'cat-room' | 'insights'][]
        ).map(([ic, t, s, route], i) => (
          <button
            key={i}
            type="button"
            className={'hbox as-button ' + (i % 2 ? 'r-l' : 'r-r')}
            onClick={() => nav.go(route)}
            aria-label={`${t} — ${s}`}
            style={{
              padding: 12,
              marginBottom: 8,
              display: 'flex',
              alignItems: 'center',
              gap: 12,
              cursor: 'pointer',
              width: '100%',
              textAlign: 'left',
            }}
          >
            <div
              className="ph-square"
              style={{ width: 36, height: 36, fontFamily: 'Pretendard', fontSize: 16, borderRadius: 14 }}
            >
              {ic}
            </div>
            <div style={{ flex: 1 }}>
              <div style={{ fontFamily: 'Pretendard', fontWeight: 700 }}>{t}</div>
              <div className="tiny">{s}</div>
            </div>
            <span style={{ fontFamily: 'Pretendard', fontSize: 22 }} aria-hidden="true">›</span>
          </button>
        ))}
      </div>
    </div>
    <TabBar active="home" />
  </div>
  );
};

export const S08_DailyCheck = () => {
  const nav = useNav();
  const { state, dispatch } = useStore();
  const { toast, flash } = useToast();

  const d = state.daily;
  const doneCount = useMemo(() => {
    let c = 0;
    if (d.food.done) c++;
    if (d.water >= 6) c++;
    if (d.sleep.done) c++;
    if (d.movement.done) c++;
    if (d.sun.done) c++;
    return c;
  }, [d]);

  const award = (key: DailyKey, label: string, before: boolean) => {
    if (!before) {
      dispatch({ type: 'points/add', delta: 10 });
      flash(`+10 ◉  ${label}`);
    }
  };

  const togglePick = (pick: string) => {
    const had = d.food.picks.includes(pick);
    dispatch({ type: 'daily/toggle-food', pick });
    if (!had && d.food.picks.length === 0) award('food', '오늘 식사 기록', d.food.done);
  };

  const setSleep = (q: string) => {
    const before = d.sleep.done;
    dispatch({ type: 'daily/sleep', quality: q });
    award('sleep', '수면 기록', before);
  };
  const setMove = (b: string) => {
    const before = d.movement.done;
    dispatch({ type: 'daily/movement', bucket: b });
    award('movement', '움직임 기록', before);
  };
  const setSun = (l: string) => {
    const before = d.sun.done;
    dispatch({ type: 'daily/sun', level: l });
    award('sun', '햇볕 기록', before);
  };
  const setWater = (n: number) => {
    const before = d.water >= 6;
    dispatch({ type: 'daily/water-set', value: n });
    if (!before && n >= 6) award('water', '물을 잘 챙겼네요', false);
  };

  return (
  <div className="screen">
    <div className="screen-scroll" style={{ padding: 'calc(46px + var(--safe-t)) 18px calc(88px + var(--safe-b, 0px))' }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 6 }}>
        <BackButton onClick={() => nav.back()} />
        <h1 className="h-title" style={{ fontSize: 22 }}>데일리 체크</h1>
      </div>
      <div className="tiny">하루 5가지 — 가볍게 톡톡</div>

      <div style={{ display: 'flex', gap: 6, marginTop: 14 }}>
        {Array.from({ length: 5 }).map((_, i) => (
          <div
            key={i}
            style={{
              flex: 1,
              height: 6,
              borderRadius: 999,
              border: '1.5px solid var(--ink)',
              background: i < doneCount ? 'var(--night)' : 'var(--paper)',
            }}
          />
        ))}
      </div>
      <div className="tiny" style={{ marginTop: 6 }}>
        {doneCount} / 5 완료 · 오늘 +{state.points} 포인트 ◉
      </div>

      {doneCount === 5 && (
        <div className="hbox accent r-r" style={{ padding: 12, marginTop: 10, textAlign: 'center' }}>
          <div style={{ fontFamily: 'Pretendard', fontWeight: 700 }}>🎉 오늘 5가지 모두 완료!</div>
          <div className="tiny" style={{ marginTop: 2 }}>꾸준함이 이음이를 키워요</div>
        </div>
      )}

      {/* 식사 */}
      <div className="hbox r-l" style={{ padding: 14, marginTop: 14 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
          <div className="ph-circle" style={{ width: 36, height: 36 }}>🍚</div>
          <div style={{ flex: 1 }}>
            <div style={{ fontFamily: 'Pretendard', fontWeight: 700 }}>오늘 식사</div>
            <div className="tiny">아침 / 점심 / 저녁 — 탭해서 토글</div>
          </div>
          <div className={'check ' + (d.food.done ? 'on' : '')}>{d.food.done ? '✓' : '○'}</div>
        </div>
        <div style={{ display: 'flex', gap: 6, marginTop: 10, flexWrap: 'wrap' }}>
          {['아침', '점심', '저녁', '간식'].map((t) => {
            const on = d.food.picks.includes(t);
            return (
              <button
                key={t}
                type="button"
                onClick={() => togglePick(t)}
                className={'chip chip-btn ' + (on ? 'solid' : 'dashed')}
                aria-pressed={on}
                style={{ background: on ? undefined : 'transparent' }}
              >
                {t}
              </button>
            );
          })}
        </div>
      </div>

      {/* 수면 */}
      <div className="hbox r-r" style={{ padding: 14, marginTop: 10 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
          <div className="ph-circle" style={{ width: 36, height: 36, overflow: 'hidden' }}><img src="/character/sleepy.webp" alt="자는 중" style={{ width: '100%', height: '100%', objectFit: 'contain' }} draggable={false} /></div>
          <div style={{ flex: 1 }}>
            <div style={{ fontFamily: 'Pretendard', fontWeight: 700 }}>어젯밤 수면</div>
            <div className="tiny">
              {d.sleep.quality ? `선택: ${d.sleep.quality}` : '취침 1:20 → 기상 7:40 · 약 6h 20m'}
            </div>
          </div>
          <div className={'check ' + (d.sleep.done ? 'on' : '')}>{d.sleep.done ? '✓' : '○'}</div>
        </div>
        <div style={{ display: 'flex', gap: 8, marginTop: 10, flexWrap: 'wrap' }}>
          {['푹잠', '뒤척', '부족', '과수면'].map((t) => (
            <button
              key={t}
              type="button"
              onClick={() => setSleep(t)}
              className={'chip chip-btn ' + (d.sleep.quality === t ? 'solid' : '')}
              aria-pressed={d.sleep.quality === t}
            >
              {t}
            </button>
          ))}
        </div>
      </div>

      {/* 움직임 */}
      <div className="hbox r-l" style={{ padding: 14, marginTop: 10 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
          <div className="ph-circle" style={{ width: 36, height: 36 }}>🚶</div>
          <div style={{ flex: 1 }}>
            <div style={{ fontFamily: 'Pretendard', fontWeight: 700 }}>몸을 움직였나</div>
            <div className="tiny">
              {d.movement.bucket ? `선택: ${d.movement.bucket}` : '스트레칭도 포함 — 정직하게'}
            </div>
          </div>
          <div className={'check ' + (d.movement.done ? 'on' : '')}>
            {d.movement.done ? '✓' : '○'}
          </div>
        </div>
        <div style={{ display: 'flex', gap: 8, marginTop: 10, flexWrap: 'wrap' }}>
          {['10분 미만', '10–30', '30+'].map((t) => (
            <button
              key={t}
              type="button"
              onClick={() => setMove(t)}
              className={'chip chip-btn ' + (d.movement.bucket === t ? 'solid' : 'dashed')}
              aria-pressed={d.movement.bucket === t}
              style={{ background: d.movement.bucket === t ? undefined : 'transparent' }}
            >
              {t}
            </button>
          ))}
        </div>
      </div>

      {/* 물 + 햇볕 */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 10, marginTop: 10 }}>
        <div className="hbox r-r" style={{ padding: 12 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            <div className="ph-circle" style={{ width: 32, height: 32 }}>💧</div>
            <div>
              <div style={{ fontFamily: 'Pretendard', fontWeight: 700 }}>물</div>
              <div className="tiny">{d.water} / 8잔 — 탭</div>
            </div>
          </div>
          <div style={{ display: 'flex', gap: 4, marginTop: 8 }}>
            {Array.from({ length: 8 }).map((_, i) => (
              <button
                key={i}
                type="button"
                onClick={() => setWater(i + 1 === d.water ? i : i + 1)}
                aria-label={`물 ${i + 1}잔`}
                style={{
                  /* 터치 타깃 44px: 히트박스(padding)와 시각(내부 span 16×22)을 분리.
                     border-box 전역 리셋 하에서 width/height 를 직접 키우면 실제
                     칩 모양이 커져버리므로, 버튼 자체는 투명 히트박스로만 쓰고
                     negative margin 으로 원래 레이아웃 폭(16×22+gap)을 유지한다. */
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  border: 'none',
                  background: 'transparent',
                  cursor: 'pointer',
                  padding: '11px 14px',
                  margin: '-11px -14px',
                }}
              >
                <span
                  style={{
                    display: 'block',
                    width: 16,
                    height: 22,
                    border: '1.5px solid var(--ink)',
                    borderRadius: 4,
                    background: i < d.water ? 'var(--ink)' : 'var(--paper)',
                  }}
                />
              </button>
            ))}
          </div>
        </div>
        <div className="hbox r-l" style={{ padding: 12 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            <div className="ph-circle" style={{ width: 32, height: 32 }}>☼</div>
            <div>
              <div style={{ fontFamily: 'Pretendard', fontWeight: 700 }}>햇볕</div>
              <div className="tiny">
                {d.sun.level ?? '바깥 공기 쐰 시간'}
              </div>
            </div>
          </div>
          <div style={{ display: 'flex', gap: 4, marginTop: 8 }}>
            {['☁', '☼', '☼☼'].map((t) => (
              <button
                key={t}
                type="button"
                onClick={() => setSun(t)}
                className={'chip chip-btn ' + (d.sun.level === t ? 'solid' : 'dashed')}
                aria-pressed={d.sun.level === t}
                style={{ background: d.sun.level === t ? undefined : 'transparent' }}
              >
                {t}
              </button>
            ))}
          </div>
        </div>
      </div>

      {doneCount === 5 && (
        <div className="hbox accent" style={{ padding: 12, marginTop: 14, textAlign: 'center' }}>
          <div className="h-title" style={{ fontSize: 18 }}>오늘 다섯 가지를 돌봤어요! 🎉</div>
          <div className="tiny">밤에 오늘 얘기 더 들려줄래?</div>
        </div>
      )}
    </div>
    {toast && <div className="toast" role="status">{toast}</div>}
    <TabBar active="home" />
  </div>
  );
};

export const S09_AIChat = () => {
  const nav = useNav();
  const { state, dispatch } = useStore();
  const [input, setInput] = useState('');
  const [typing, setTyping] = useState(false);
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: scrollBehavior() });
  }, [state.aiChat, typing]);

  const send = (text?: string) => {
    const t = (text ?? input).trim();
    if (!t || typing) return;
    dispatch({ type: 'ai-chat/append', msg: { role: 'user', text: t } });
    setInput('');
    setTyping(true);
    // 로컬 시뮬레이션 모드 (VITE_AI_ENABLED=false): backend 미경유
    if (!AI_ENABLED) {
      setTimeout(() => {
        dispatch({ type: 'ai-chat/append', msg: simulateAiReply(t) });
        setTyping(false);
      }, 700 + Math.random() * 400);
      return;
    }
    // backend 결선: maskPII로 PII 제거 후 전송 → CLOVA(mock) 응답.
    // 원문 평문은 기기를 떠나지 않는다(liv-I1). 실패 시 로컬 폴백.
    void (async () => {
      try {
        const { text: aiText } = await sendAiChat(t);
        dispatch({
          type: 'ai-chat/append',
          msg: { role: 'bot', text: aiText || simulateAiReply(t).text },
        });
      } catch {
        dispatch({ type: 'ai-chat/append', msg: simulateAiReply(t) });
      } finally {
        setTyping(false);
      }
    })();
  };

  const quick = ['잠이 안 와요', '집이 너무 조용해', '오늘 기분 그저 그래', '루틴 추천'];

  return (
    <div className="screen">
      <div
        ref={scrollRef}
        className="screen-scroll"
        style={{ padding: 'calc(46px + var(--safe-t)) 14px calc(140px + var(--safe-b, 0px))' }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 4 }}>
          <BackButton onClick={() => nav.back()} />
          <h1 className="h-title" style={{ fontSize: 22 }}>AI 코칭 (낮 모드)</h1>
        </div>
        <div className="tiny" style={{ marginBottom: 14 }}>
          이음이는 자는 중 — 작은 비서가 답해줘요
        </div>

        <ChatThread
          msgs={state.aiChat}
          typing={typing}
          avatar={<div className="ph-circle" style={{ width: 28, height: 28, fontSize: 11, flex: 'none' }}>✦</div>}
        />

        <h2 className="h-label" style={{ marginTop: 18, marginBottom: 6 }}>자주 묻는 것</h2>
        <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap' }}>
          {quick.map((t, i) => (
            <button
              key={i}
              type="button"
              onClick={() => send(t)}
              className="chip chip-btn"
              style={{ background: 'var(--paper)', borderWidth: '0.5px' }}
            >
              {t}
            </button>
          ))}
        </div>
      </div>

      <ChatInputRow
        value={input}
        onChange={setInput}
        onSend={() => send()}
        placeholder="비서에게 말 걸기..."
        ariaLabel="비서에게 말 걸기"
      />
      <TabBar active="home" />
    </div>
  );
};
