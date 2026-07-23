import { useEffect, useRef, useState } from 'react';
import { BackButton, CatSketch, MoodFace, useToast } from '../components/primitives';
import { ChatThread } from '../components/chat';
import { useNav } from '../lib/router';
import { scrollBehavior } from '../lib/scroll';
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
  dateParts,
  formatDateKey,
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
  const voiceDialogRef = useRef<HTMLDivElement>(null);
  const selectedMode = state.chatDiaryMode;
  const selectedMaxTurns = state.chatDiaryMaxTurns;
  const isShortMode = selectedMode === 'short';

  // 보이스 모달 — 열릴 때 첫 버튼 focus + Esc 로 닫기(A11Y-08, 로직 불변·포커스 관리만 추가).
  useEffect(() => {
    if (!voiceModalOpen) return;
    voiceDialogRef.current?.querySelector<HTMLElement>('button')?.focus();
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') setVoiceModalOpen(false);
    };
    document.addEventListener('keydown', onKey);
    return () => document.removeEventListener('keydown', onKey);
  }, [voiceModalOpen]);
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
      background: 'linear-gradient(180deg, var(--night) 0%, var(--night-2) 100%)',
      color: 'var(--paper)',
    }}
  >
    <svg
      width="100%"
      height="100%"
      viewBox="0 0 375 800"
      preserveAspectRatio="xMidYMid slice"
      style={{ position: 'absolute', inset: 0, opacity: 0.35 }}
    >
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
        <circle key={i} cx={x} cy={y} r="1.4" fill="var(--paper)" />
      ))}
    </svg>
    <div className="screen-scroll" style={{ padding: 'calc(60px + var(--safe-t)) 24px calc(100px + var(--safe-b, 0px))' }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
        <BackButton onClick={() => nav.back()} tone="var(--accent-soft)" />
        <div className="h-section" style={{ color: 'var(--accent-soft)' }}>
          저녁 회고 — 시작 전
        </div>
      </div>
      <h1 className="h-display" style={{ marginTop: 14, color: 'var(--paper)', fontSize: 36 }}>
        오늘도 고생했어.
      </h1>
      <div
        className="handwriting"
        style={{ color: 'var(--accent-soft)', marginTop: 10, fontSize: 18, fontWeight: 700 }}
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
          background: 'var(--paper)',
          color: 'var(--ink)',
          border: '1.5px solid var(--ink)',
          padding: 14,
          marginTop: 20,
        }}
      >
        <div className="tiny" style={{ color: 'var(--pencil)' }}>낮 동안 메모 요약</div>
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

      <h2 className="h-label" style={{ marginTop: 18, color: 'var(--accent-soft)' }}>
        오늘은 어떻게 할까?
      </h2>
      <div style={{ display: 'flex', gap: 8, marginTop: 8 }}>
        <button
          type="button"
          className="hbox as-button"
          aria-pressed={selectedMode === 'full'}
          style={{
            flex: 1,
            padding: 10,
            textAlign: 'center',
            border: '1.5px solid var(--ink)',
            color: selectedMode === 'full' ? 'var(--paper)' : 'var(--ink)',
            background: selectedMode === 'full' ? 'var(--accent)' : 'var(--paper)',
            cursor: 'pointer',
          }}
          onClick={() => selectMode('full')}
        >
          <div style={{ fontFamily: 'Pretendard', fontWeight: 700 }}>✦ 대화</div>
          <div className="tiny" style={{ color: 'inherit' }}>5턴 챗</div>
        </button>
        <button
          type="button"
          className="hbox as-button"
          aria-pressed={selectedMode === 'short'}
          style={{
            flex: 1,
            padding: 10,
            textAlign: 'center',
            border: '1.5px solid var(--ink)',
            color: selectedMode === 'short' ? 'var(--paper)' : 'var(--ink)',
            background: selectedMode === 'short' ? 'var(--accent)' : 'var(--paper)',
            cursor: 'pointer',
          }}
          onClick={() => selectMode('short')}
        >
          <div style={{ fontFamily: 'Pretendard', fontWeight: 700 }}>줄글 기록</div>
          <div className="tiny" style={{ color: 'inherit' }}>3줄 일기</div>
        </button>
        <button
          type="button"
          className="hbox as-button"
          style={{
            flex: 1,
            padding: 10,
            textAlign: 'center',
            border: '1.5px solid var(--ink)',
            color: 'var(--ink)',
            background: 'var(--paper)',
            cursor: 'pointer',
          }}
          onClick={() => setVoiceModalOpen(true)}
        >
          <div style={{ fontFamily: 'Pretendard', fontWeight: 700 }}>보이스 기록</div>
          <div className="tiny" style={{ color: 'var(--pencil)' }}>곧 출시</div>
        </button>
      </div>
    </div>
    <div className="pin-bottom" style={{ bottom: 'calc(28px + var(--safe-b, 0px))' }}>
      <button
        type="button"
        onClick={() => nav.go('chat-diary')}
        className="btn primary block"
        style={{ cursor: 'pointer', fontFamily: 'inherit' }}
      >
        {selectedMaxTurns}턴 회고 시작하기 →
      </button>
      <button
        type="button"
        className="tiny as-button"
        onClick={() => nav.back()}
        style={{
          display: 'block',
          width: '100%',
          textAlign: 'center',
          color: 'var(--accent-soft)',
          marginTop: 8,
          cursor: 'pointer',
        }}
      >
        오늘 건너뛰기
      </button>
    </div>
    {voiceModalOpen && (
      <div
        style={{
          position: 'absolute',
          inset: 0,
          background: 'var(--scrim)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          padding: 24,
          zIndex: 100,
        }}
        onClick={() => setVoiceModalOpen(false)}
      >
        <div
          ref={voiceDialogRef}
          role="dialog"
          aria-modal="true"
          aria-label="보이스 회고"
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
  const initedRef = useRef(false);
  const maxTurns = state.chatDiaryMaxTurns as ChatSessionMaxTurns;

  // 로컬 대화가 비어 있으면 서버 세션도 새로 맞춰서 같은 턴 정책으로 시작한다.
  useEffect(() => {
    if (state.chatDiary.length > 0) {
      // 대화가 채워지면 플래그 해제 → 이후 reset(빈 상태 재진입) 시 재초기화 허용.
      initedRef.current = false;
      return;
    }
    // StrictMode(dev) 이중 실행 가드: 인트로 2회 append·서버 세션 reset 2회 발사 방지.
    if (initedRef.current) return;
    initedRef.current = true;
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
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: scrollBehavior() });
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
      style={{ padding: 'calc(46px + var(--safe-t)) 14px calc(96px + var(--safe-b, 0px))' }}
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
          <BackButton
            onClick={() => {
              if (confirm('회고를 중단할까요? (대화는 보존됩니다)')) nav.back();
            }}
          />
          <h1 className="h-title">오늘의 회고</h1>
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
              background: i < turn ? 'var(--night)' : 'var(--paper)',
              border: '1.5px solid var(--ink)',
              borderRadius: 999,
            }}
          />
        ))}
      </div>

      <ChatThread
        msgs={state.chatDiary}
        typing={typing}
        avatar={
          <div
            className="ph-circle"
            style={{ width: 30, height: 30, background: 'var(--paper-2)', overflow: 'hidden', flex: 'none' }}
          >
            <CatSketch size={32} mood="wink" />
          </div>
        }
        style={{ marginTop: 14 }}
      />
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
        aria-label="이음이에게 답하기"
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
  const { toast, flash } = useToast();
  const generatedDiary = state.chatDiaryGeneratedDiary;
  const diaryMoods = moodsFromEmotion(generatedDiary?.emotion);
  const summaryRows = emotionSummary(generatedDiary?.emotion);

  // Pull recent user answers from chat-diary to build a fresh diary preview.
  const userAnswers = state.chatDiary.filter((m) => m.role === 'user').map((m) => m.text);
  // 실날짜 기준(레거시 5월 27일 고정 제거). 서버 diary_date 가 없으면 오늘로 저장.
  const now = new Date();
  const todayKey = formatDateKey(now.getFullYear(), now.getMonth() + 1, now.getDate());
  const { month: todayMonth, day: todayDay } = dateParts(todayKey);
  const datePrefix = `${todayMonth}월 ${todayDay}일`;
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
    // 서버가 준 diary_date 우선, 없으면 항상 실제 오늘(todayKey)로 저장.
    const diaryDate = generatedDiary?.diary_date ?? todayKey;
    const diaryDay = dateParts(diaryDate).day;
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
    <div className="screen-scroll" style={{ padding: 'calc(46px + var(--safe-t)) 18px calc(80px + var(--safe-b, 0px))' }}>
      <div className="tiny" style={{ color: 'var(--pencil)' }}>{state.chatDiaryMaxTurns}턴 완료 — 일기로 마무리</div>
      <h1 className="h-display" style={{ marginTop: 8, fontSize: 32 }}>
        오늘은 어떤
        <br />
        하루였어?
      </h1>

      {analyzing ? (
        <div className="hbox r-l" style={{ padding: 22, marginTop: 18, textAlign: 'center', border: '1.5px solid var(--ink)' }}>
          <div style={{ display: 'flex', justifyContent: 'center' }}>
            <CatSketch size={78} mood="wink" />
          </div>
          <div className="tiny" style={{ marginTop: 10, color: 'var(--pencil)' }}>이음이가 일기를 정리하는 중…</div>
          <div style={{ display: 'flex', gap: 5, justifyContent: 'center', marginTop: 10 }}>
            <span className="typing-dot" />
            <span className="typing-dot" />
            <span className="typing-dot" />
          </div>
        </div>
      ) : (
        <>
      <div className="hbox r-l" style={{ padding: 14, marginTop: 14, border: '1.5px solid var(--ink)' }}>
        <div className="tiny" style={{ color: 'var(--pencil)' }}>이음이가 읽은 오늘 감정</div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 14, marginTop: 10 }}>
          <div
            className="ph-circle"
            style={{ width: 56, height: 56, background: 'var(--paper-2)', overflow: 'hidden', flex: 'none' }}
          >
            <MoodFace mood={diaryMoods[0]} size={48} />
          </div>
          <div style={{ flex: 1, display: 'flex', flexDirection: 'column', gap: 8 }}>
            {summaryRows.map(([n, , p], i) => (
              <div key={i} style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                <span className="tiny" style={{ width: 32, flex: 'none' }}>{n}</span>
                <div className="bar" style={{ flex: 1, height: 8, background: 'var(--paper-2)' }}>
                  <i
                    style={{
                      width: p,
                      background: i === 0 ? 'rgba(168,86,75,0.75)' : 'rgba(43,24,16,0.39)',
                      borderRight: 'none',
                    }}
                  />
                </div>
                <span className="tiny" style={{ width: 30, flex: 'none', textAlign: 'right', fontWeight: 700 }}>
                  {p}
                </span>
              </div>
            ))}
          </div>
        </div>
        <div className="tiny" style={{ marginTop: 10 }}>
          키워드:{' '}
          {keywords.map((k, i) => (
            <span key={i} className="chip" style={{ marginRight: 4, borderWidth: '0.5px', background: 'var(--paper)' }}>
              {k}
            </span>
          ))}
        </div>
      </div>

      <div
        className="hbox r-r"
        style={{ padding: 14, marginTop: 12, background: 'var(--cream)', border: '1.5px solid var(--ink)' }}
        >
          <div style={{ display: 'flex', justifyContent: 'space-between' }}>
            <div className="tiny" style={{ color: 'var(--pencil)' }}>생성된 일기</div>
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

      <div className="hbox night r-l" style={{ padding: 12, marginTop: 12, border: '1.5px solid var(--ink)' }}>
        <div className="tiny" style={{ color: 'var(--cream)' }}>
          내일 한 가지
        </div>
        <div className="h-title" style={{ color: 'var(--paper)', fontSize: 18, marginTop: 4 }}>
          {tomorrowLine}
        </div>
        <div style={{ display: 'flex', gap: 6, marginTop: 8 }}>
          <button
            type="button"
            onClick={() => flash('⏰ 내일 알람으로 추가했어요')}
            className="chip chip-btn"
            style={{ background: 'var(--banner)', color: 'var(--paper)', borderWidth: '1.5px', cursor: 'pointer', fontFamily: 'inherit' }}
          >
            설정
          </button>
          <button
            type="button"
            onClick={() => flash('다음에 알려줄게요')}
            className="chip chip-btn"
            style={{ background: 'var(--paper)', borderWidth: '1.5px', cursor: 'pointer', fontFamily: 'inherit' }}
          >
            나중에
          </button>
        </div>
      </div>
        </>
      )}
    </div>
    {toast && <div className="toast" role="status">{toast}</div>}
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
      style={{ position: 'absolute', inset: 0, background: 'var(--scrim)' }}
    />

    <div
      className="screen-scroll"
      style={{ display: 'flex', flexDirection: 'column', padding: 24 }}
    >
    <div
      style={{
        margin: 'auto 0',
        padding: 24,
        background: 'var(--paper)',
        border: '1.5px solid var(--ink)',
        borderRadius: 14,
        boxShadow: '4px 6px 0 rgba(0,0,0,0.25)',
      }}
    >
      <h1 className="tiny" style={{ textAlign: 'center', color: 'var(--pencil)' }}>
        오늘 회고 완료 — 보상 도착
      </h1>

      <div style={{ display: 'flex', justifyContent: 'center', marginTop: 16 }}>
        <div
          style={{
            padding: '5px 18px',
            borderRadius: 999,
            background: 'var(--accent-2)',
            color: 'var(--paper)',
          }}
        >
          <span style={{ fontFamily: 'Pretendard', fontWeight: 700, fontSize: 22 }}>+80 포인트</span>
        </div>
      </div>

      <div
        style={{
          marginTop: 16,
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          gap: 6,
        }}
      >
        <div
          className="ph-square"
          style={{ width: 130, height: 90, borderWidth: '0.5px', background: 'var(--paper-2)', overflow: 'hidden' }}
        >
          <CatSketch size={78} mood="happy" />
        </div>
        <div className="h-title" style={{ fontSize: 20, marginTop: 4 }}>
          참치 츄르 🐟
        </div>
        <div className="tiny" style={{ color: 'var(--pencil)' }}>이음이가 제일 좋아하는 간식</div>
      </div>

      <div
        style={{
          marginTop: 16,
          display: 'flex',
          alignItems: 'center',
          gap: 10,
          justifyContent: 'center',
        }}
      >
        <span style={{ fontFamily: 'Pretendard', fontWeight: 700, fontSize: 20, color: 'var(--night)' }}>
          {state.streak - 1} → {state.streak}일
        </span>
      </div>
      <div className="bar" style={{ marginTop: 10, background: 'var(--paper-2)' }}>
        <i style={{ width: Math.min(100, (state.streak / 14) * 100) + '%', background: 'var(--night)', borderRightColor: 'var(--night)' }} />
      </div>
      <div className="tiny" style={{ textAlign: 'center', marginTop: 6, color: 'var(--pencil)' }}>
        오늘도 만나서 좋았어
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
