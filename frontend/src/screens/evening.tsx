import { useEffect, useRef, useState } from 'react';
import { CatSketch, ImgPh, MoodFace } from '../components/primitives';
import { useNav } from '../lib/router';
import {
  AI_ENABLED,
  clearChatSessionCache,
  sendAiChat,
  startAiChatSession,
  type ChatSessionMaxTurns,
} from '../lib/api';
import {
  CHAT_DIARY_FULL_TURNS,
  CHAT_DIARY_INTRO,
  CHAT_DIARY_SHORT_TURNS,
  CHAT_DIARY_TURNS,
  TODAY_DAY,
  dateParts,
  useStore,
} from '../lib/store';
import type { ChatDiaryMode, Mood } from '../lib/store';

// 10-13 · Evening recap entry / Chat Diary / Mood finalize / Reward modal

const modeToTurns = (mode: ChatDiaryMode): ChatSessionMaxTurns =>
  mode === 'short' ? CHAT_DIARY_SHORT_TURNS : CHAT_DIARY_FULL_TURNS;

const moodsFromEmotion = (emotion?: string): Mood[] => {
  switch (emotion) {
    case 'happy':
    case 'excited':
      return ['😊', '😌'];
    case 'sad':
      return ['😢', '😣'];
    case 'angry':
      return ['😡', '😣'];
    case 'anxious':
      return ['😣', '😢'];
    case 'grateful':
      return ['😊', '😌'];
    case 'tired':
      return ['😣', '😌'];
    case 'calm':
    default:
      return ['😌', '😊'];
  }
};

const emotionSummary = (emotion?: string): [string, string, string][] => {
  switch (emotion) {
    case 'happy':
      return [
        ['기쁨', 'var(--paper-2)', '45%'],
        ['차분', 'var(--accent-soft)', '30%'],
        ['뿌듯', '#fff', '25%'],
      ];
    case 'sad':
      return [
        ['슬픔', 'var(--paper-2)', '45%'],
        ['피곤', 'var(--accent-soft)', '30%'],
        ['차분', '#fff', '25%'],
      ];
    case 'angry':
      return [
        ['답답', 'var(--paper-2)', '40%'],
        ['피곤', 'var(--accent-soft)', '35%'],
        ['차분', '#fff', '25%'],
      ];
    case 'anxious':
      return [
        ['불안', 'var(--paper-2)', '45%'],
        ['피곤', 'var(--accent-soft)', '30%'],
        ['안도', '#fff', '25%'],
      ];
    case 'grateful':
      return [
        ['고마움', 'var(--paper-2)', '45%'],
        ['차분', 'var(--accent-soft)', '30%'],
        ['기쁨', '#fff', '25%'],
      ];
    case 'tired':
      return [
        ['피곤', 'var(--paper-2)', '45%'],
        ['차분', 'var(--accent-soft)', '30%'],
        ['안도', '#fff', '25%'],
      ];
    case 'calm':
    default:
      return [
        ['차분', 'var(--paper-2)', '45%'],
        ['안도', 'var(--accent-soft)', '30%'],
        ['뿌듯', '#fff', '25%'],
      ];
  }
};

const fallbackKeywordsFromAnswers = (answers: string[]): string[] =>
  answers.length > 0
    ? Array.from(
        new Set(
          answers
            .slice(0, 3)
            .map((a) => a.trim().split(/[\s,.!?·]+/).filter(Boolean)[0])
            .filter((w): w is string => Boolean(w)),
        ),
      ).slice(0, 3)
    : ['오늘', '기록'];

export const S10_RecapStart = () => {
  const nav = useNav();
  const { state, dispatch } = useStore();
  const [voiceModalOpen, setVoiceModalOpen] = useState(false);
  const selectedMode = state.chatDiaryMode;
  const selectedMaxTurns = state.chatDiaryMaxTurns;
  const isShortMode = selectedMode === 'short';
  // 낮 동안의 기록(AI 채팅·데일리체크)을 회고 입력으로 인계 — 없으면 빈상태. (C)경계: 로컬 유지.
  const d = state.daily;
  const memos: string[] = [
    ...state.aiChat
      .filter((m) => m.role === 'user')
      .slice(-2)
      .map((m) => '💬 ' + m.text.trim().slice(0, 18)),
    ...(d.food.done ? ['🍚 식사 기록'] : []),
    ...(d.water >= 6 ? [`💧 물 ${d.water}컵`] : []),
    ...(d.movement.done ? ['🚶 운동'] : []),
    ...(d.sun.done ? ['☼ 햇볕'] : []),
  ];

  const selectMode = (mode: ChatDiaryMode) => {
    const maxTurns = modeToTurns(mode);
    const modeChanged =
      state.chatDiaryMode !== mode || state.chatDiaryMaxTurns !== maxTurns;
    dispatch({ type: 'chat-diary/configure', mode, maxTurns });
    if (modeChanged && (state.chatDiary.length > 0 || state.chatDiaryGeneratedDiary)) {
      dispatch({ type: 'chat-diary/reset' });
    }
  };

  return (
  <div
    className="screen"
    style={{
      background: 'linear-gradient(180deg, var(--night) 0%, #4a2f1e 100%)',
      color: 'var(--paper)',
    }}
  >
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
    <div className="screen-scroll" style={{ padding: '60px 24px calc(100px + var(--safe-b, 0px))' }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
        <span
          style={{ fontFamily: 'Pretendard', fontSize: 22, color: 'var(--accent-soft)', cursor: 'pointer' }}
          onClick={() => nav.back()}
        >
          ‹
        </span>
        <div className="h-section" style={{ color: 'var(--accent-soft)' }}>
          저녁 회고 — 시작 전
        </div>
      </div>
      <div className="h-display" style={{ marginTop: 14, color: 'var(--paper)' }}>
        오늘도
        <br />
        고생했어.
      </div>
      <div
        className="handwriting"
        style={{ color: 'var(--accent-soft)', marginTop: 10, fontSize: 20 }}
      >
        {isShortMode ? '3번만 나누는 짧은 회고' : '5분이면 충분해 · 5턴 대화'}
      </div>

      <div style={{ marginTop: 24, display: 'flex', justifyContent: 'center' }}>
        <div
          style={{
            background: 'var(--paper)',
            borderRadius: 16,
            padding: 14,
            border: '2px solid var(--ink)',
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
          color: 'var(--ink)',
          padding: 14,
          marginTop: 20,
        }}
      >
        <div className="h-section">낮 동안 메모해둔 것</div>
        <div style={{ display: 'flex', flexDirection: 'column', gap: 6, marginTop: 8 }}>
          {memos.length > 0 ? (
            memos.map((t, i) => (
              <div key={i} style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                <div className="check on sq" style={{ width: 16, height: 16 }}>
                  ✓
                </div>
                <span className="body">{t}</span>
              </div>
            ))
          ) : (
            <span className="body" style={{ opacity: 0.85 }}>
              오늘은 낮 기록이 없어요 — 그래도 천천히 시작해요 🌙
            </span>
          )}
        </div>
        {memos.length > 0 && (
          <div className="tiny" style={{ marginTop: 8, color: 'var(--accent)' }}>
            ↳ 대화에서 이걸 바탕으로 물어볼게
          </div>
        )}
      </div>

      <div className="h-label" style={{ marginTop: 18, color: 'var(--accent-soft)' }}>
        오늘은 어떻게 할까?
      </div>
      <div style={{ display: 'flex', gap: 8, marginTop: 8 }}>
        <div
          className={`hbox${selectedMode === 'full' ? ' accent' : ''}`}
          style={{
            flex: 1,
            padding: 10,
            textAlign: 'center',
            color: 'var(--ink)',
            background: selectedMode === 'full' ? undefined : 'var(--paper)',
            cursor: 'pointer',
          }}
          onClick={() => selectMode('full')}
        >
          <div style={{ fontFamily: 'Pretendard', fontWeight: 700 }}>✦ 대화</div>
          <div className="tiny">5턴 챗</div>
        </div>
        <div
          className={`hbox${selectedMode === 'short' ? ' accent' : ''}`}
          style={{
            flex: 1,
            padding: 10,
            textAlign: 'center',
            color: 'var(--ink)',
            background: selectedMode === 'short' ? undefined : 'var(--paper)',
            cursor: 'pointer',
          }}
          onClick={() => selectMode('short')}
        >
          <div style={{ fontFamily: 'Pretendard', fontWeight: 700 }}>✎ 짧게</div>
          <div className="tiny">3줄 일기</div>
        </div>
        <div
          className="hbox"
          style={{
            flex: 1,
            padding: 10,
            textAlign: 'center',
            color: 'var(--ink)',
            background: 'var(--paper)',
            cursor: 'pointer',
          }}
          onClick={() => setVoiceModalOpen(true)}
        >
          <div style={{ fontFamily: 'Pretendard', fontWeight: 700 }}>🎙 보이스</div>
          <div className="tiny">곧 출시</div>
        </div>
      </div>
    </div>
    <div style={{ position: 'absolute', bottom: 'calc(28px + var(--safe-b, 0px))', left: 24, right: 24 }}>
      <button
        type="button"
        onClick={() => nav.go('chat-diary')}
        className="btn primary block"
        style={{ cursor: 'pointer', fontFamily: 'inherit' }}
      >
        {selectedMaxTurns}턴 회고 시작하기 →
      </button>
      <div
        className="tiny"
        onClick={() => nav.back()}
        style={{
          textAlign: 'center',
          color: 'var(--accent-soft)',
          marginTop: 8,
          cursor: 'pointer',
        }}
      >
        오늘 건너뛰기
      </div>
    </div>
    {voiceModalOpen && (
      <div
        style={{
          position: 'absolute',
          inset: 0,
          background: 'rgba(20, 12, 8, 0.58)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          padding: 24,
          zIndex: 100,
        }}
        onClick={() => setVoiceModalOpen(false)}
      >
        <div
          className="hbox"
          style={{
            width: '100%',
            maxWidth: 280,
            padding: 18,
            background: 'var(--paper)',
            color: 'var(--ink)',
            textAlign: 'center',
          }}
          onClick={(e) => e.stopPropagation()}
        >
          <div className="h-section">보이스 회고</div>
          <div className="body" style={{ marginTop: 8 }}>
            곧 지원돼요
          </div>
          <button
            type="button"
            onClick={() => setVoiceModalOpen(false)}
            className="btn primary block"
            style={{ marginTop: 16, cursor: 'pointer', fontFamily: 'inherit' }}
          >
            확인
          </button>
        </div>
      </div>
    )}
  </div>
  );
};

export const S11_ChatDiary = () => {
  const nav = useNav();
  const { state, dispatch } = useStore();
  const [input, setInput] = useState('');
  const [typing, setTyping] = useState(false);
  const scrollRef = useRef<HTMLDivElement>(null);
  const maxTurns = state.chatDiaryMaxTurns as ChatSessionMaxTurns;

  // 로컬 대화가 비어 있으면 서버 세션도 새로 맞춰서 같은 턴 정책으로 시작한다.
  useEffect(() => {
    if (state.chatDiary.length > 0) return;
    setTyping(false);
    setInput('');
    dispatch({ type: 'chat-diary/set-generated-diary', diary: null });
    clearChatSessionCache(maxTurns);
    void startAiChatSession({ maxTurns, reset: true }).catch(() => undefined);
    dispatch({ type: 'chat-diary/append', msg: CHAT_DIARY_INTRO });
    const timer = window.setTimeout(() => {
      dispatch({
        type: 'chat-diary/append',
        msg: { role: 'bot', text: CHAT_DIARY_TURNS[0].question, hint: CHAT_DIARY_TURNS[0].hint },
      });
    }, 500);
    return () => window.clearTimeout(timer);
  }, [dispatch, maxTurns, state.chatDiary.length]);

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: 'smooth' });
  }, [state.chatDiary, typing]);

  const userTurns = state.chatDiary.filter((m) => m.role === 'user').length;
  const turn = Math.min(userTurns, maxTurns);
  const done = turn >= maxTurns;

  const finishRecap = (closing?: string) => {
    dispatch({
      type: 'chat-diary/append',
      msg: {
        role: 'bot',
        text: closing || '잘 들었어. 이걸로 오늘 일기를 정리해줄게.\n잠깐만 기다려줘 ✎',
      },
    });
    setTimeout(() => nav.go('mood-finalize'), 1200);
  };

  // Clova 미연동/실패 시 폴백: 기존 하드코딩 질문.
  const fallbackQuestion = (nextTurn: number) => {
    const q = CHAT_DIARY_TURNS[Math.min(nextTurn, CHAT_DIARY_TURNS.length - 1)];
    dispatch({ type: 'chat-diary/append', msg: { role: 'bot', text: q.question, hint: q.hint } });
  };

  const send = () => {
    const t = input.trim();
    if (!t) return;
    dispatch({ type: 'chat-diary/append', msg: { role: 'user', text: t } });
    setInput('');
    const nextTurn = userTurns + 1;
    setTyping(true);

    // 로컬 시뮬레이션 모드 (VITE_AI_ENABLED=false): 기존 하드코딩 질문 흐름 유지.
    if (!AI_ENABLED) {
      setTimeout(() => {
        setTyping(false);
        if (nextTurn < maxTurns) fallbackQuestion(nextTurn);
        else finishRecap();
      }, 800 + Math.random() * 400);
      return;
    }

    // backend 결선: 회고 발화를 Clova(mock/실)로 보내 실제 응답을 받는다.
    // diary가 오면 서버가 해당 턴에서 일기 생성을 끝낸 상태다.
    void (async () => {
      try {
        const { text: aiText, diary } = await sendAiChat(t, { maxTurns });
        setTyping(false);
        if (diary) {
          dispatch({
            type: 'chat-diary/set-generated-diary',
            diary: {
              diary_date: diary.diary_date,
              title: diary.title,
              content: diary.content,
              emotion: diary.emotion,
              satisfaction: diary.satisfaction,
              keywords: diary.keywords,
            },
          });
          clearChatSessionCache(maxTurns);
          finishRecap(aiText);
          return;
        }
        if (nextTurn < maxTurns) {
          dispatch({
            type: 'chat-diary/append',
            msg: {
              role: 'bot',
              text: aiText || CHAT_DIARY_TURNS[Math.min(nextTurn, CHAT_DIARY_TURNS.length - 1)].question,
            },
          });
        } else {
          finishRecap(aiText);
        }
      } catch {
        setTyping(false);
        if (nextTurn < maxTurns) fallbackQuestion(nextTurn);
        else finishRecap();
      }
    })();
  };

  return (
  <div className="screen">
    <div
      ref={scrollRef}
      className="screen-scroll"
      style={{ padding: '46px 14px calc(96px + var(--safe-b, 0px))' }}
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
            style={{ fontFamily: 'Pretendard', fontSize: 22, cursor: 'pointer' }}
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
          {turn} / {maxTurns}턴 ⟲
        </button>
      </div>
      <div style={{ display: 'flex', gap: 6, marginTop: 6 }}>
        {Array.from({ length: maxTurns }, (_, i) => (
          <div
            key={i}
            style={{
              flex: 1,
              height: 6,
              background: i < turn ? 'var(--ink)' : 'var(--paper)',
              border: '1.5px solid var(--ink)',
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
                style={{ width: 30, height: 30, background: 'var(--paper-2)', overflow: 'hidden', flex: 'none' }}
              >
                <CatSketch size={32} mood="wink" />
              </div>
              <div className="bubble bubble-bot">
                <div className="body" style={{ whiteSpace: 'pre-wrap' }}>{m.text}</div>
                {m.hint && (
                  <div className="tiny" style={{ marginTop: 4, color: 'var(--accent)' }}>{m.hint}</div>
                )}
              </div>
            </div>
          ) : (
            <div key={i} style={{ display: 'flex', justifyContent: 'flex-end' }}>
              <div className="bubble bubble-user">
                <div className="body" style={{ whiteSpace: 'pre-wrap' }}>{m.text}</div>
              </div>
            </div>
          ),
        )}
        {typing && (
          <div style={{ display: 'flex', gap: 8, alignItems: 'flex-end' }}>
            <div
              className="ph-circle"
              style={{ width: 30, height: 30, background: 'var(--paper-2)', overflow: 'hidden', flex: 'none' }}
            >
              <CatSketch size={32} mood="wink" />
            </div>
            <div className="bubble bubble-bot" style={{ padding: '12px 16px' }}>
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
  const generatedDiary = state.chatDiaryGeneratedDiary;
  const diaryMoods = moodsFromEmotion(generatedDiary?.emotion);
  const summaryRows = emotionSummary(generatedDiary?.emotion);
  const flash = (m: string) => {
    setToast(m);
    setTimeout(() => setToast(null), 1400);
  };

  // Pull recent user answers from chat-diary to build a fresh diary preview.
  const userAnswers = state.chatDiary.filter((m) => m.role === 'user').map((m) => m.text);
  const datePrefix = `5월 ${TODAY_DAY}일`;
  const bodyPreview =
    generatedDiary?.content
      ? generatedDiary.content
      : userAnswers.length > 0
      ? `${datePrefix}. ${userAnswers
          .slice(0, 4)
          .map((t) => t.trim().replace(/\n+/g, ' '))
          .join('\n')}`
      : `${datePrefix}. 점심으로 우동 한 그릇이 위로였다.\n긴 회의로 피곤했고, 끝난 뒤에 숨 돌릴 5분이\n없었던 게 가장 무거웠다. 내일은 일정 사이에\n3분의 틈을 만들어보기로 했다.`;

  const tomorrowLine =
    userAnswers[userAnswers.length - 1] ??
    (state.chatDiaryMode === 'short'
      ? '내일도 짧게라도 하루를 돌아보기'
      : '회의 종료 후 · 3분 호흡 알람');

  // 서버 AI 키워드가 없을 때만 로컬 휴리스틱으로 fallback한다.
  const keywords =
    generatedDiary?.keywords && generatedDiary.keywords.length > 0
      ? generatedDiary.keywords.slice(0, 3)
      : fallbackKeywordsFromAnswers(userAnswers);

  // 분석 로딩 → 결과(성공) 전환 (온디바이스 시뮬, 서버 미전송 — (C)경계).
  const [analyzing, setAnalyzing] = useState(true);
  useEffect(() => {
    const t = setTimeout(() => setAnalyzing(false), 1100);
    return () => clearTimeout(t);
  }, []);

  const save = () => {
    const diaryDate = generatedDiary?.diary_date;
    const diaryDay = diaryDate ? dateParts(diaryDate).day : TODAY_DAY;
    dispatch({
      type: 'diary/save',
      entry: {
        day: diaryDay,
        date: diaryDate,
        moods: diaryMoods,
        keywords,
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
    clearChatSessionCache(state.chatDiaryMaxTurns as ChatSessionMaxTurns);
    dispatch({ type: 'chat-diary/reset' });
    nav.go('reward');
  };

  return (
  <div className="screen">
    <div className="screen-scroll" style={{ padding: '46px 18px calc(80px + var(--safe-b, 0px))' }}>
      <div className="h-section">{state.chatDiaryMaxTurns}턴 완료 — 일기로 마무리</div>
      <div className="h-display" style={{ marginTop: 8 }}>
        오늘은 이런
        <br />
        하루였어 ⌇
      </div>

      {analyzing ? (
        <div className="hbox r-l" style={{ padding: 22, marginTop: 18, textAlign: 'center' }}>
          <div style={{ display: 'flex', justifyContent: 'center' }}>
            <CatSketch size={78} mood="wink" />
          </div>
          <div className="h-section" style={{ marginTop: 10 }}>이음이가 일기를 정리하는 중…</div>
          <div style={{ display: 'flex', gap: 5, justifyContent: 'center', marginTop: 10 }}>
            <span className="typing-dot" />
            <span className="typing-dot" />
            <span className="typing-dot" />
          </div>
        </div>
      ) : (
        <>
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
              <MoodFace mood={diaryMoods[0]} size={24} />
            </div>
          </div>
          <div style={{ flex: 1, display: 'flex', flexDirection: 'column', gap: 6 }}>
            {summaryRows.map(([n, c, p], i) => (
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
          키워드:{' '}
          {keywords.map((k, i) => (
            <span key={i} className="chip dashed" style={{ marginRight: 4 }}>
              {k}
            </span>
          ))}
        </div>
      </div>

      <div
        className="hbox r-r"
        style={{ padding: 14, marginTop: 12, background: 'var(--cream)' }}
        >
          <div style={{ display: 'flex', justifyContent: 'space-between' }}>
            <div className="h-section">생성된 일기</div>
          <button
            type="button"
            onClick={() => flash('✎ 일기 직접 수정은 곧 지원돼요')}
            className="tiny"
            style={{ background: 'transparent', border: 'none', cursor: 'pointer', fontFamily: 'inherit', color: 'var(--pencil)' }}
          >
            ✎ 수정
          </button>
        </div>
        {generatedDiary?.title && (
          <div className="h-title" style={{ marginTop: 8, fontSize: 18 }}>
            {generatedDiary.title}
          </div>
        )}
        <div
          className="handwriting"
          style={{ marginTop: 8, fontSize: 17, lineHeight: 1.5, whiteSpace: 'pre-wrap' }}
        >
          {bodyPreview}
        </div>
      </div>

      <div className="hbox night r-l" style={{ padding: 12, marginTop: 12 }}>
        <div className="h-section" style={{ color: 'var(--accent-soft)' }}>
          내일 한 가지
        </div>
        <div className="h-title" style={{ color: 'var(--paper)', fontSize: 18, marginTop: 2 }}>
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
            style={{ background: 'var(--paper)', cursor: 'pointer', fontFamily: 'inherit' }}
          >
            나중에
          </button>
        </div>
      </div>
        </>
      )}
    </div>
    {toast && <div className="toast">{toast}</div>}
    <div
      style={{
        position: 'absolute',
        bottom: 'calc(16px + var(--safe-b, 0px))',
        left: 18,
        right: 18,
        display: 'flex',
        gap: 8,
      }}
    >
      <button
        type="button"
        onClick={() => {
          clearChatSessionCache(state.chatDiaryMaxTurns as ChatSessionMaxTurns);
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
        disabled={analyzing}
        className="btn primary block"
        style={{ cursor: analyzing ? 'wait' : 'pointer', fontFamily: 'inherit', opacity: analyzing ? 0.55 : 1 }}
      >
        {analyzing ? '정리 중…' : '저장하기'}
      </button>
    </div>
  </div>
  );
};

export const S13_Reward = () => {
  const nav = useNav();
  const { state } = useStore();
  return (
  <div className="screen">
    <div
      style={{ position: 'absolute', inset: 0, background: 'rgba(26,26,26,0.55)' }}
    />
    <div style={{ position: 'absolute', inset: 0, padding: 18, opacity: 0.3 }}>
      <div className="hbox" style={{ height: 100, marginTop: 50 }} />
      <div className="hbox" style={{ height: 140, marginTop: 10 }} />
    </div>

    <div
      className="screen-scroll"
      style={{ display: 'flex', flexDirection: 'column', padding: 24 }}
    >
    <div
      style={{
        margin: 'auto 0',
        padding: 24,
        background: 'var(--paper)',
        border: '2px solid var(--ink)',
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
          <span style={{ fontFamily: 'Pretendard', fontSize: 22 }}>+80 포인트</span>
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
        <span style={{ fontFamily: 'Pretendard', fontWeight: 700, fontSize: 22, color: 'var(--accent-soft)' }}>
          {state.streak - 1} → {state.streak}일 연속
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
