import { KeyboardEvent, useEffect, useMemo, useRef, useState } from 'react';
import { CatSketch, StatusBar, TabBar } from '../components/primitives';
import { useNav } from '../lib/router';
import { DailyKey, simulateAiReply, useStore } from '../lib/store';

// 06-09 · Home Day / Home Night / Daily Check / AI Chat

export const S06_HomeDay = () => {
  const nav = useNav();
  const { state } = useStore();
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
  return (
  <div className="phone-inner">
    <StatusBar mode="day" time="10:42 AM" />
    <div className="phone-scroll" style={{ padding: '46px 18px 88px' }}>
      <div
        style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'flex-start',
          marginBottom: 12,
        }}
      >
        <div>
          <div className="tiny">5월 27일 · 수요일</div>
          <div className="h-title" style={{ marginTop: 2 }}>
            좋은 아침,
            <br />
            해미 ☀
          </div>
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
          <span className="chip dashed">🔥 {state.streak}일</span>
        </div>
      </div>

      <div className="hbox day r-l" style={{ padding: 16, marginTop: 6 }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <div>
            <div className="h-section" style={{ color: '#7a5a18' }}>
              이음이는 자는 중
            </div>
            <div className="h-title" style={{ marginTop: 2, fontSize: 20 }}>
              밤 10시에 깨어나요
            </div>
          </div>
          <div className="chip" style={{ background: '#fff' }}>
            ⏰ 10:00 PM
          </div>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 14, marginTop: 10 }}>
          <CatSketch size={86} sleeping />
          <div className="handwriting" style={{ color: '#5a4a20' }}>
            "쿠울… 쿠울…
            <br />
            이따 만나, 친구"
          </div>
        </div>
        <div className="bar" style={{ marginTop: 12 }}>
          <i style={{ width: '55%' }} />
        </div>
        <div className="tiny" style={{ marginTop: 4 }}>
          휴식중 · 다음 깨어남까지 11시간 18분
        </div>
      </div>

      <div
        className="hbox r-r"
        onClick={() => nav.go('daily-check')}
        style={{ padding: 14, marginTop: 12, cursor: 'pointer' }}
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
                className="ph-square"
                style={{
                  width: 44,
                  height: 44,
                  margin: '0 auto',
                  background: on ? '#3a2414' : '#f5e6cf',
                  color: on ? '#f5e6cf' : '#3a2414',
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
      </div>

      <div
        className="hbox accent r-l"
        onClick={() => nav.go('ai-chat')}
        style={{
          padding: 14,
          marginTop: 12,
          display: 'flex',
          alignItems: 'center',
          gap: 12,
          cursor: 'pointer',
        }}
      >
        <div className="ph-circle" style={{ width: 40, height: 40, background: '#fff' }}>
          ✦
        </div>
        <div style={{ flex: 1 }}>
          <div style={{ fontFamily: 'Patrick Hand', fontWeight: 700 }}>
            AI 코칭에게 물어봐요
          </div>
          <div className="tiny">"점심 뭐 먹지?" "잠이 안 와요"</div>
        </div>
        <span className="handwriting" style={{ fontSize: 24 }}>
          ›
        </span>
      </div>

      <div
        style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 10, marginTop: 12 }}
      >
        {(
          [
            ['오늘 컨디션', '😌 평온', '지난주와 비슷'],
            ['이번 주', '3 / 7 일', '+1회로 목표'],
            ['포인트', '◉ 240', '보상 2 개'],
            ['키우기', '옷장 NEW', '보러가기 ›'],
          ] as [string, string, string][]
        ).map(([t, big, sub], i) => (
          <div
            key={i}
            className={'hbox r-' + (i % 2 ? 'l' : 'r')}
            onClick={i === 3 ? () => nav.go('cat-room') : undefined}
            style={{ padding: 12, cursor: i === 3 ? 'pointer' : 'default' }}
          >
            <div className="tiny">{t}</div>
            <div className="h-title" style={{ fontSize: 18, marginTop: 2 }}>
              {big}
            </div>
            <div className="tiny" style={{ marginTop: 2 }}>
              {sub}
            </div>
          </div>
        ))}
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
    className="phone-inner"
    style={{ background: 'linear-gradient(180deg, #f5e6cf 0%, #ead0a6 70%, #d8a777 100%)' }}
  >
    <StatusBar mode="night" time="10:14 PM" />
    <div className="phone-scroll" style={{ padding: '46px 18px 88px' }}>
      <div
        style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'flex-start',
          marginBottom: 12,
        }}
      >
        <div>
          <div className="tiny">5월 27일 · 수요일 밤</div>
          <div className="h-title" style={{ marginTop: 2 }}>
            이음이가
            <br />
            깨어났어요 ☾
          </div>
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
          <span className="chip dashed">🔥 {state.streak}일</span>
        </div>
      </div>

      <div
        className="hbox night r-l"
        style={{ padding: 16, marginTop: 6, position: 'relative', overflow: 'hidden' }}
      >
        <svg width="100%" height="40" style={{ position: 'absolute', top: 6, left: 0, opacity: 0.4 }}>
          {[
            [40, 12],
            [120, 24],
            [260, 16],
            [320, 30],
          ].map(([x, y], i) => (
            <circle key={i} cx={x} cy={y} r="1.2" fill="#f5e6cf" />
          ))}
        </svg>
        <div className="h-section" style={{ color: '#d8a777' }}>
          저녁 회고 · 매일 밤
        </div>
        <div className="h-title" style={{ color: '#f5e6cf', marginTop: 2, fontSize: 22 }}>
          "오늘 하루, 잠깐
          <br />
          같이 돌아볼까?"
        </div>
        <div style={{ display: 'flex', alignItems: 'flex-end', gap: 12, marginTop: 14 }}>
          <div
            style={{
              background: '#f5e6cf',
              borderRadius: 12,
              padding: 8,
              border: '1.5px solid #3a2414',
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
        <div style={{ fontFamily: 'Caveat', fontSize: 42, color: '#8c4a1f' }}>🔥12</div>
        <div style={{ flex: 1 }}>
          <div style={{ fontFamily: 'Patrick Hand', fontWeight: 700 }}>12일 연속!</div>
          <div className="tiny">+3일이면 새 옷 잠금해제 🎁</div>
        </div>
        <div style={{ display: 'flex', gap: 3 }}>
          {[1, 1, 1, 1, 1, 0, 0].map((on, i) => (
            <div
              key={i}
              className="ph-circle"
              style={{
                width: 14,
                height: 14,
                background: on ? '#8c4a1f' : '#fff',
                borderColor: '#3a2414',
              }}
            />
          ))}
        </div>
      </div>

      <div className="hbox r-l" style={{ padding: 12, marginTop: 12 }}>
        <div className="h-section" style={{ marginBottom: 8 }}>
          오늘 미리 표시한 감정
        </div>
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
                background: on ? '#ead0a6' : '#fff',
                fontSize: 18,
              }}
            >
              {e}
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
          <div
            key={i}
            className={'hbox ' + (i % 2 ? 'r-l' : 'r-r')}
            onClick={() => nav.go(route)}
            style={{
              padding: 12,
              marginBottom: 8,
              display: 'flex',
              alignItems: 'center',
              gap: 12,
              cursor: 'pointer',
            }}
          >
            <div
              className="ph-square"
              style={{ width: 36, height: 36, fontFamily: 'Patrick Hand', fontSize: 16 }}
            >
              {ic}
            </div>
            <div style={{ flex: 1 }}>
              <div style={{ fontFamily: 'Patrick Hand', fontWeight: 700 }}>{t}</div>
              <div className="tiny">{s}</div>
            </div>
            <span style={{ fontFamily: 'Caveat', fontSize: 22 }}>›</span>
          </div>
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
  const [toast, setToast] = useState<string | null>(null);

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

  const flash = (msg: string) => {
    setToast(msg);
    setTimeout(() => setToast(null), 1400);
  };

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
    if (!before && n >= 6) award('water', '물 6잔 달성', false);
  };

  return (
  <div className="phone-inner">
    <StatusBar mode="day" time="12:08 PM" />
    <div className="phone-scroll" style={{ padding: '46px 18px 88px' }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 6 }}>
        <span
          style={{ fontFamily: 'Caveat', fontSize: 22, cursor: 'pointer' }}
          onClick={() => nav.back()}
        >
          ‹
        </span>
        <div className="h-title">데일리 체크</div>
      </div>
      <div className="tiny">하루 5가지 — 가볍게 톡톡</div>

      <div className="bar" style={{ marginTop: 14 }}>
        <i style={{ width: (doneCount / 5) * 100 + '%' }} />
      </div>
      <div className="tiny" style={{ marginTop: 4 }}>
        {doneCount} / 5 완료 · 오늘 누적 포인트 {state.points} ◉
      </div>

      {/* 식사 */}
      <div className="hbox r-l" style={{ padding: 14, marginTop: 14 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
          <div className="ph-circle" style={{ width: 36, height: 36 }}>🍚</div>
          <div style={{ flex: 1 }}>
            <div style={{ fontFamily: 'Patrick Hand', fontWeight: 700 }}>오늘 식사</div>
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
          <div className="ph-circle" style={{ width: 36, height: 36 }}>😴</div>
          <div style={{ flex: 1 }}>
            <div style={{ fontFamily: 'Patrick Hand', fontWeight: 700 }}>어젯밤 수면</div>
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
              className={'chip chip-btn ' + (d.sleep.quality === t ? 'accent' : '')}
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
            <div style={{ fontFamily: 'Patrick Hand', fontWeight: 700 }}>몸을 움직였나</div>
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
              className={'chip chip-btn ' + (d.movement.bucket === t ? 'accent' : 'dashed')}
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
              <div style={{ fontFamily: 'Patrick Hand', fontWeight: 700 }}>물</div>
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
                  width: 16,
                  height: 22,
                  border: '1.5px solid #3a2414',
                  borderRadius: 4,
                  background: i < d.water ? '#8c4a1f' : '#f5e6cf',
                  cursor: 'pointer',
                  padding: 0,
                }}
              />
            ))}
          </div>
        </div>
        <div className="hbox r-l" style={{ padding: 12 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            <div className="ph-circle" style={{ width: 32, height: 32 }}>☼</div>
            <div>
              <div style={{ fontFamily: 'Patrick Hand', fontWeight: 700 }}>햇볕</div>
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
                className={'chip chip-btn ' + (d.sun.level === t ? 'accent' : 'dashed')}
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
          <div className="h-title" style={{ fontSize: 18 }}>오늘 5체크 완성! 🎉</div>
          <div className="tiny">밤 회고 때 더 깊은 분석을 해줄게</div>
        </div>
      )}
    </div>
    {toast && <div className="toast">{toast}</div>}
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
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: 'smooth' });
  }, [state.aiChat, typing]);

  const send = (text?: string) => {
    const t = (text ?? input).trim();
    if (!t) return;
    dispatch({ type: 'ai-chat/append', msg: { role: 'user', text: t } });
    setInput('');
    setTyping(true);
    setTimeout(() => {
      const reply = simulateAiReply(t);
      dispatch({ type: 'ai-chat/append', msg: reply });
      setTyping(false);
    }, 700 + Math.random() * 400);
  };

  const onKey = (e: KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      send();
    }
  };

  const quick = ['잠이 안 와요', '집이 너무 조용해', '오늘 기분 그저 그래', '루틴 추천'];

  return (
    <div className="phone-inner">
      <StatusBar mode="day" time="2:42 PM" />
      <div
        ref={scrollRef}
        className="phone-scroll"
        style={{ padding: '46px 14px 140px' }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 4 }}>
          <span
            style={{ fontFamily: 'Caveat', fontSize: 22, cursor: 'pointer' }}
            onClick={() => nav.back()}
          >
            ‹
          </span>
          <div className="h-title">AI 코칭 (낮 모드)</div>
        </div>
        <div className="tiny" style={{ marginBottom: 14 }}>
          이음이는 자는 중 — 작은 비서가 답해줘요
        </div>

        <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
          {state.aiChat.map((m, i) =>
            m.role === 'bot' ? (
              <div key={i} style={{ display: 'flex', gap: 8, alignItems: 'flex-end' }}>
                <div className="ph-circle" style={{ width: 28, height: 28, fontSize: 11, flex: 'none' }}>✦</div>
                <div className="hbox" style={{ padding: '10px 12px', maxWidth: 280 }}>
                  <div className="body" style={{ whiteSpace: 'pre-wrap' }}>{m.text}</div>
                </div>
              </div>
            ) : (
              <div key={i} style={{ display: 'flex', justifyContent: 'flex-end' }}>
                <div className="hbox accent" style={{ padding: '10px 12px', maxWidth: 260 }}>
                  <div className="body" style={{ whiteSpace: 'pre-wrap' }}>{m.text}</div>
                </div>
              </div>
            ),
          )}
          {typing && (
            <div style={{ display: 'flex', gap: 8, alignItems: 'flex-end' }}>
              <div className="ph-circle" style={{ width: 28, height: 28, fontSize: 11, flex: 'none' }}>✦</div>
              <div className="hbox" style={{ padding: '12px 16px' }}>
                <span className="typing-dot" />
                <span className="typing-dot" />
                <span className="typing-dot" />
              </div>
            </div>
          )}
        </div>

        <div className="h-label" style={{ marginTop: 18, marginBottom: 6 }}>자주 묻는 것</div>
        <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap' }}>
          {quick.map((t, i) => (
            <button
              key={i}
              type="button"
              onClick={() => send(t)}
              className="chip dashed chip-btn"
              style={{ background: 'transparent', border: '1.5px dashed #3a2414' }}
            >
              {t}
            </button>
          ))}
        </div>
      </div>

      <form
        onSubmit={(e) => {
          e.preventDefault();
          send();
        }}
        className="input-row"
        style={{ bottom: 64 }}
      >
        <input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={onKey}
          placeholder="비서에게 말 걸기..."
          autoFocus
        />
        <button
          type="submit"
          className="btn primary"
          style={{
            padding: 10,
            width: 42,
            height: 42,
            borderRadius: '50%',
            fontFamily: 'inherit',
            cursor: 'pointer',
            flex: 'none',
          }}
        >
          →
        </button>
      </form>
      <TabBar active="home" />
    </div>
  );
};
