import { KeyboardEvent, useEffect, useRef, useState } from 'react';
import { CatSketch, ImgPh, StatusBar } from '../components/primitives';
import { useNav } from '../lib/router';
import {
  CHAT_DIARY_INTRO,
  CHAT_DIARY_TURNS,
  TODAY_DAY,
  useStore,
} from '../lib/store';

// 10-13 · Evening recap entry / Chat Diary / Mood finalize / Reward modal

export const S10_RecapStart = () => {
  const nav = useNav();
  return (
  <div
    className="phone-inner"
    style={{
      background: 'linear-gradient(180deg, #2b1810 0%, #4a2f1e 100%)',
      color: '#f5e6cf',
    }}
  >
    <StatusBar mode="night" time="10:18 PM" />
    <svg width="100%" height="100%" style={{ position: 'absolute', inset: 0, opacity: 0.35 }}>
      {[
        [40, 90],
        [120, 140],
        [300, 80],
        [260, 200],
        [60, 260],
        [330, 260],
        [180, 170],
        [80, 420],
      ].map(([x, y], i) => (
        <circle key={i} cx={x} cy={y} r="1.4" fill="#f5e6cf" />
      ))}
    </svg>
    <div className="phone-scroll" style={{ padding: '60px 24px 100px' }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
        <span
          style={{ fontFamily: 'Caveat', fontSize: 22, color: '#d8a777', cursor: 'pointer' }}
          onClick={() => nav.back()}
        >
          ‹
        </span>
        <div className="h-section" style={{ color: '#d8a777' }}>
          저녁 회고 — 시작 전
        </div>
      </div>
      <div className="h-display" style={{ marginTop: 14, color: '#f5e6cf' }}>
        오늘도
        <br />
        고생했어.
      </div>
      <div
        className="handwriting"
        style={{ color: '#d8a777', marginTop: 10, fontSize: 20 }}
      >
        5분이면 충분해 · 5턴 대화
      </div>

      <div style={{ marginTop: 24, display: 'flex', justifyContent: 'center' }}>
        <div
          style={{
            background: '#f5e6cf',
            borderRadius: 16,
            padding: 14,
            border: '2px solid #3a2414',
            transform: 'rotate(-1.5deg)',
          }}
        >
          <CatSketch size={120} mood="happy" />
        </div>
      </div>

      <div
        className="hbox"
        style={{
          background: 'rgba(251,248,243,0.95)',
          color: '#3a2414',
          padding: 14,
          marginTop: 20,
        }}
      >
        <div className="h-section">낮 동안 메모해둔 것</div>
        <div style={{ display: 'flex', flexDirection: 'column', gap: 6, marginTop: 8 }}>
          {['🍜 점심 우동', '🚶 산책 안 함', '💧 물 4컵', '😣 회의 후 피곤'].map((t, i) => (
            <div key={i} style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
              <div className="check on sq" style={{ width: 16, height: 16 }}>
                ✓
              </div>
              <span className="body">{t}</span>
            </div>
          ))}
        </div>
        <div className="tiny" style={{ marginTop: 8, color: '#8c4a1f' }}>
          ↳ 대화에서 이걸 바탕으로 물어볼게
        </div>
      </div>

      <div className="h-label" style={{ marginTop: 18, color: '#d8a777' }}>
        오늘은 어떻게 할까?
      </div>
      <div style={{ display: 'flex', gap: 8, marginTop: 8 }}>
        <div
          className="hbox accent"
          style={{ flex: 1, padding: 10, textAlign: 'center', color: '#3a2414' }}
        >
          <div style={{ fontFamily: 'Patrick Hand', fontWeight: 700 }}>✦ 대화</div>
          <div className="tiny">5턴 챗</div>
        </div>
        <div
          className="hbox"
          style={{
            flex: 1,
            padding: 10,
            textAlign: 'center',
            color: '#3a2414',
            background: '#f5e6cf',
          }}
        >
          <div style={{ fontFamily: 'Patrick Hand', fontWeight: 700 }}>✎ 짧게</div>
          <div className="tiny">3줄 일기</div>
        </div>
        <div
          className="hbox"
          style={{
            flex: 1,
            padding: 10,
            textAlign: 'center',
            color: '#3a2414',
            background: '#f5e6cf',
          }}
        >
          <div style={{ fontFamily: 'Patrick Hand', fontWeight: 700 }}>🎙 보이스</div>
          <div className="tiny">곧 출시</div>
        </div>
      </div>
    </div>
    <div style={{ position: 'absolute', bottom: 28, left: 24, right: 24 }}>
      <button
        type="button"
        onClick={() => nav.go('chat-diary')}
        className="btn primary block"
        style={{ cursor: 'pointer', fontFamily: 'inherit' }}
      >
        시작하기 →
      </button>
      <div
        className="tiny"
        onClick={() => nav.back()}
        style={{
          textAlign: 'center',
          color: '#d8a777',
          marginTop: 8,
          cursor: 'pointer',
        }}
      >
        오늘 건너뛰기
      </div>
    </div>
  </div>
  );
};

export const S11_ChatDiary = () => {
  const nav = useNav();
  const { state, dispatch } = useStore();
  const [input, setInput] = useState('');
  const [typing, setTyping] = useState(false);
  const scrollRef = useRef<HTMLDivElement>(null);
  const seeded = useRef(false);

  // Seed first bot message + first question on mount if empty.
  // ref guard: StrictMode(dev)의 이중 effect 발화로 인한 인삿말·질문 중복 방지.
  useEffect(() => {
    if (seeded.current) return;
    seeded.current = true;
    if (state.chatDiary.length === 0) {
      dispatch({ type: 'chat-diary/append', msg: CHAT_DIARY_INTRO });
      setTimeout(() => {
        dispatch({
          type: 'chat-diary/append',
          msg: { role: 'bot', text: CHAT_DIARY_TURNS[0].question, hint: CHAT_DIARY_TURNS[0].hint },
        });
      }, 500);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: 'smooth' });
  }, [state.chatDiary, typing]);

  const userTurns = state.chatDiary.filter((m) => m.role === 'user').length;
  const turn = Math.min(userTurns, 5);
  const done = turn >= 5;

  const send = () => {
    const t = input.trim();
    if (!t) return;
    dispatch({ type: 'chat-diary/append', msg: { role: 'user', text: t } });
    setInput('');
    const nextTurn = userTurns + 1;
    setTyping(true);
    setTimeout(() => {
      setTyping(false);
      if (nextTurn < 5) {
        const q = CHAT_DIARY_TURNS[nextTurn];
        dispatch({
          type: 'chat-diary/append',
          msg: { role: 'bot', text: q.question, hint: q.hint },
        });
      } else {
        dispatch({
          type: 'chat-diary/append',
          msg: {
            role: 'bot',
            text: '잘 들었어. 이걸로 오늘 일기를 정리해줄게.\n잠깐만 기다려줘 ✎',
          },
        });
        setTimeout(() => nav.go('mood-finalize'), 1200);
      }
    }, 800 + Math.random() * 400);
  };

  return (
  <div className="phone-inner">
    <StatusBar mode="night" time="10:24 PM" />
    <div
      ref={scrollRef}
      className="phone-scroll"
      style={{ padding: '46px 14px 96px', position: 'relative' }}
    >
      <div
        style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          marginBottom: 4,
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <span
            style={{ fontFamily: 'Caveat', fontSize: 22, cursor: 'pointer' }}
            onClick={() => {
              if (confirm('회고를 중단할까요? (대화는 보존됩니다)')) nav.back();
            }}
          >
            ‹
          </span>
          <div className="h-title">오늘의 회고</div>
        </div>
        <button
          type="button"
          onClick={() => dispatch({ type: 'chat-diary/reset' })}
          className="chip"
          style={{ cursor: 'pointer', fontFamily: 'inherit' }}
          title="대화 다시 시작"
        >
          {turn} / 5턴 ⟲
        </button>
      </div>
      <div style={{ display: 'flex', gap: 6, marginTop: 6 }}>
        {[0, 1, 2, 3, 4].map((i) => (
          <div
            key={i}
            style={{
              flex: 1,
              height: 6,
              background: i < turn ? '#8c4a1f' : '#f5e6cf',
              border: '1.5px solid #3a2414',
              borderRadius: 3,
            }}
          />
        ))}
      </div>

      <div style={{ display: 'flex', flexDirection: 'column', gap: 10, marginTop: 14 }}>
        {state.chatDiary.map((m, i) =>
          m.role === 'bot' ? (
            <div key={i} style={{ display: 'flex', gap: 8, alignItems: 'flex-end' }}>
              <div
                className="ph-circle"
                style={{ width: 30, height: 30, background: '#ead0a6', overflow: 'hidden', flex: 'none' }}
              >
                <CatSketch size={32} mood="wink" />
              </div>
              <div className="hbox" style={{ padding: '10px 12px', maxWidth: 280 }}>
                <div className="body" style={{ whiteSpace: 'pre-wrap' }}>{m.text}</div>
                {m.hint && (
                  <div className="tiny" style={{ marginTop: 4, color: '#8c4a1f' }}>{m.hint}</div>
                )}
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
            <div
              className="ph-circle"
              style={{ width: 30, height: 30, background: '#ead0a6', overflow: 'hidden', flex: 'none' }}
            >
              <CatSketch size={32} mood="wink" />
            </div>
            <div className="hbox" style={{ padding: '12px 16px' }}>
              <span className="typing-dot" />
              <span className="typing-dot" />
              <span className="typing-dot" />
            </div>
          </div>
        )}
      </div>
    </div>
    <form
      onSubmit={(e) => {
        e.preventDefault();
        send();
      }}
      className="input-row"
      style={{ bottom: 0 }}
    >
      <input
        value={input}
        onChange={(e) => setInput(e.target.value)}
        placeholder={done ? '회고 완료 — 일기로 정리 중...' : '이음이에게 답해주세요...'}
        disabled={done || typing}
        autoFocus
      />
      <button
        type="submit"
        className="btn ink"
        disabled={done || typing || !input.trim()}
        style={{
          padding: 10,
          width: 46,
          height: 46,
          borderRadius: '50%',
          cursor: done || typing || !input.trim() ? 'not-allowed' : 'pointer',
          fontFamily: 'inherit',
          flex: 'none',
          opacity: !input.trim() ? 0.55 : 1,
        }}
      >
        →
      </button>
    </form>
  </div>
  );
};

export const S12_MoodFinalize = () => {
  const nav = useNav();
  const { state, dispatch } = useStore();
  const [toast, setToast] = useState<string | null>(null);
  const flash = (m: string) => {
    setToast(m);
    setTimeout(() => setToast(null), 1400);
  };

  // Pull recent user answers from chat-diary to build a fresh diary preview.
  const userAnswers = state.chatDiary.filter((m) => m.role === 'user').map((m) => m.text);
  const datePrefix = `5월 ${TODAY_DAY}일`;
  const bodyPreview =
    userAnswers.length > 0
      ? `${datePrefix}. ${userAnswers
          .slice(0, 4)
          .map((t) => t.trim().replace(/\n+/g, ' '))
          .join('\n')}`
      : `${datePrefix}. 점심으로 우동 한 그릇이 위로였다.\n긴 회의로 피곤했고, 끝난 뒤에 숨 돌릴 5분이\n없었던 게 가장 무거웠다. 내일은 일정 사이에\n3분의 틈을 만들어보기로 했다.`;

  const tomorrowLine = userAnswers[4] ?? '회의 종료 후 · 3분 호흡 알람';

  const save = () => {
    dispatch({
      type: 'diary/save',
      entry: {
        day: TODAY_DAY,
        moods: ['😣', '😌', '😊'],
        keywords: userAnswers[0] ? [userAnswers[0].slice(0, 8)] : ['긴 회의', '우동'],
        body: bodyPreview,
        check: {
          food: state.daily.food.done,
          water: state.daily.water >= 6,
          sleep: state.daily.sleep.done,
          movement: state.daily.movement.done,
          sun: state.daily.sun.done,
        },
        tomorrow: tomorrowLine,
        createdAt: Date.now(),
      },
    });
    dispatch({ type: 'points/add', delta: 80 });
    dispatch({ type: 'streak/inc' });
    dispatch({ type: 'chat-diary/reset' });
    nav.go('reward');
  };

  return (
  <div className="phone-inner">
    <StatusBar mode="night" time="10:31 PM" />
    <div className="phone-scroll" style={{ padding: '46px 18px 80px' }}>
      <div className="h-section">5턴 완료 — 일기로 마무리</div>
      <div className="h-display" style={{ marginTop: 8 }}>
        오늘은 이런
        <br />
        하루였어 ⌇
      </div>

      <div className="hbox r-l" style={{ padding: 14, marginTop: 14 }}>
        <div className="h-section">이음이가 읽은 오늘 감정</div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginTop: 8 }}>
          <div style={{ position: 'relative', width: 90, height: 90 }}>
            <svg width="90" height="90" viewBox="0 0 90 90">
              <circle cx="45" cy="45" r="38" stroke="#3a2414" strokeWidth="1.5" fill="#fff" />
              <path
                d="M45 7 A 38 38 0 0 1 76 60 L 45 45 Z"
                fill="#ead0a6"
                stroke="#3a2414"
                strokeWidth="1.5"
              />
              <path
                d="M45 7 A 38 38 0 0 0 14 30 L 45 45 Z"
                fill="#d8a777"
                stroke="#3a2414"
                strokeWidth="1.5"
              />
              <path
                d="M45 45 L 76 60 A 38 38 0 0 1 14 30 Z"
                fill="#fff"
                stroke="#3a2414"
                strokeWidth="1.5"
              />
            </svg>
            <div
              style={{
                position: 'absolute',
                inset: 0,
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
              }}
            >
              <span style={{ fontFamily: 'Caveat', fontSize: 22 }}>😣</span>
            </div>
          </div>
          <div style={{ flex: 1, display: 'flex', flexDirection: 'column', gap: 6 }}>
            {(
              [
                ['피곤', '#ead0a6', '45%'],
                ['차분', '#d8a777', '30%'],
                ['뿌듯', '#fff', '25%'],
              ] as [string, string, string][]
            ).map(([n, c, p], i) => (
              <div key={i} style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                <div
                  className="ph-circle"
                  style={{ width: 12, height: 12, background: c }}
                />
                <span className="tiny" style={{ flex: 1 }}>
                  {n}
                </span>
                <span className="tiny" style={{ fontWeight: 700 }}>
                  {p}
                </span>
              </div>
            ))}
          </div>
        </div>
        <div className="tiny" style={{ marginTop: 8 }}>
          키워드: <span className="chip dashed">긴 회의</span>{' '}
          <span className="chip dashed">우동</span>{' '}
          <span className="chip dashed">5분이 없음</span>
        </div>
      </div>

      <div
        className="hbox r-r"
        style={{ padding: 14, marginTop: 12, background: '#fff5e1' }}
      >
        <div style={{ display: 'flex', justifyContent: 'space-between' }}>
          <div className="h-section">생성된 일기</div>
          <button
            type="button"
            onClick={() => flash('✎ 일기 직접 수정은 곧 지원돼요')}
            className="tiny"
            style={{ background: 'transparent', border: 'none', cursor: 'pointer', fontFamily: 'inherit', color: '#7a5634' }}
          >
            ✎ 수정
          </button>
        </div>
        <div
          className="handwriting"
          style={{ marginTop: 8, fontSize: 17, lineHeight: 1.5, whiteSpace: 'pre-wrap' }}
        >
          {bodyPreview}
        </div>
      </div>

      <div className="hbox night r-l" style={{ padding: 12, marginTop: 12 }}>
        <div className="h-section" style={{ color: '#d8a777' }}>
          내일 한 가지
        </div>
        <div className="h-title" style={{ color: '#f5e6cf', fontSize: 18, marginTop: 2 }}>
          {tomorrowLine}
        </div>
        <div style={{ display: 'flex', gap: 6, marginTop: 8 }}>
          <button
            type="button"
            onClick={() => flash('⏰ 내일 알람으로 추가했어요')}
            className="chip chip-btn accent"
            style={{ cursor: 'pointer', fontFamily: 'inherit' }}
          >
            설정
          </button>
          <button
            type="button"
            onClick={() => flash('다음에 알려줄게요')}
            className="chip chip-btn"
            style={{ background: '#f5e6cf', cursor: 'pointer', fontFamily: 'inherit' }}
          >
            나중에
          </button>
        </div>
      </div>
    </div>
    {toast && <div className="toast">{toast}</div>}
    <div
      style={{
        position: 'absolute',
        bottom: 16,
        left: 18,
        right: 18,
        display: 'flex',
        gap: 8,
      }}
    >
      <button
        type="button"
        onClick={() => {
          dispatch({ type: 'chat-diary/reset' });
          nav.go('chat-diary');
        }}
        className="btn block"
        style={{ cursor: 'pointer', fontFamily: 'inherit' }}
      >
        다시 쓰기
      </button>
      <button
        type="button"
        onClick={save}
        className="btn primary block"
        style={{ cursor: 'pointer', fontFamily: 'inherit' }}
      >
        저장하기
      </button>
    </div>
  </div>
  );
};

export const S13_Reward = () => {
  const nav = useNav();
  const { state } = useStore();
  return (
  <div className="phone-inner">
    <div
      style={{ position: 'absolute', inset: 0, background: 'rgba(26,26,26,0.55)' }}
    />
    <div style={{ position: 'absolute', inset: 0, padding: 18, opacity: 0.3 }}>
      <div className="hbox" style={{ height: 100, marginTop: 50 }} />
      <div className="hbox" style={{ height: 140, marginTop: 10 }} />
    </div>

    <div
      className="phone-scroll"
      style={{ display: 'flex', flexDirection: 'column', padding: 24 }}
    >
    <div
      style={{
        margin: 'auto 0',
        padding: 24,
        background: '#f5e6cf',
        border: '2px solid #3a2414',
        borderRadius: 20,
        boxShadow: '4px 6px 0 rgba(0,0,0,0.25)',
      }}
    >
      <div className="tiny" style={{ textAlign: 'center' }}>
        오늘 회고 완료 — 보상 도착
      </div>
      <div className="h-display" style={{ marginTop: 6, textAlign: 'center' }}>
        🎉
      </div>

      <div style={{ display: 'flex', justifyContent: 'center', marginTop: 4 }}>
        <div
          className="hbox accent"
          style={{
            padding: '6px 14px',
            borderRadius: 999,
            transform: 'rotate(-1.5deg)',
          }}
        >
          <span style={{ fontFamily: 'Caveat', fontSize: 22 }}>+80 포인트</span>
        </div>
      </div>

      <div
        className="hbox dashed"
        style={{
          marginTop: 16,
          padding: 18,
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          gap: 6,
        }}
      >
        <ImgPh w={120} h={100} label="아이템 일러스트" />
        <div className="h-title" style={{ fontSize: 20 }}>
          참치 츄르 🐟
        </div>
        <div className="tiny">이음이가 제일 좋아하는 간식</div>
      </div>

      <div
        style={{
          marginTop: 14,
          display: 'flex',
          alignItems: 'center',
          gap: 10,
          justifyContent: 'center',
        }}
      >
        <span style={{ fontFamily: 'Caveat', fontSize: 28, color: '#8c4a1f' }}>
          🔥 {state.streak - 1} → {state.streak}일
        </span>
      </div>
      <div className="bar" style={{ marginTop: 10 }}>
        <i style={{ width: Math.min(100, (state.streak / 14) * 100) + '%' }} />
      </div>
      <div className="tiny" style={{ textAlign: 'center', marginTop: 4 }}>
        14일 달성 시 → 새 옷 잠금해제 ({Math.max(0, 14 - state.streak)}일 남음)
      </div>
      <div className="tiny" style={{ textAlign: 'center', marginTop: 4 }}>
        총 포인트 {state.points} ◉ · 일기 {state.diaries.length}건
      </div>

      <div style={{ display: 'flex', gap: 8, marginTop: 18 }}>
        <button
          type="button"
          onClick={() => nav.reset('home-night')}
          className="btn block"
          style={{ cursor: 'pointer', fontFamily: 'inherit' }}
        >
          홈으로
        </button>
        <button
          type="button"
          onClick={() => nav.reset('cat-room')}
          className="btn primary block"
          style={{ cursor: 'pointer', fontFamily: 'inherit' }}
        >
          먹이주기 →
        </button>
      </div>
    </div>
    </div>
  </div>
  );
};
