import { useEffect, useRef, useState } from 'react';
import { BackButton, TabBar } from '../components/primitives';
import { ChatInputRow, ChatThread } from '../components/chat';
import { useNav } from '../lib/router';
import { scrollBehavior } from '../lib/scroll';
import { sendCoachingMessage, type CoachTurn } from '../lib/api';

// S23 · 밤 코칭 (건강냥 Medlife) — guardrail-first 코칭 대화.
// 건강냥이 BE: POST /api/v1/coaching/messages (stateless, 클라가 history 보관).
// 의료 요구는 BE에서 면책으로 단락된다. PII는 전송 직전 마스킹(liv-I1).

type Msg = { role: 'user' | 'bot'; text: string };

const INTRO: Msg = {
  role: 'bot',
  text: '오늘 하루도 고생 많았어요. 잠들기 전에, 몸이나 마음 중 뭐가 제일 신경 쓰여요?',
};

const COACH_AVATAR = (
  <div className="ph-circle" style={{ width: 28, height: 28, flex: 'none', overflow: 'hidden' }}>
    <img src="/character/head-glasses.webp" alt="건강냥" style={{ width: '100%', height: '100%', objectFit: 'contain' }} draggable={false} />
  </div>
);

export const S23_Coach = () => {
  const nav = useNav();
  const [msgs, setMsgs] = useState<Msg[]>([INTRO]);
  const [input, setInput] = useState('');
  const [typing, setTyping] = useState(false);
  const [err, setErr] = useState(false);
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: scrollBehavior() });
  }, [msgs, typing]);

  const send = (text?: string) => {
    const t = (text ?? input).trim();
    if (!t || typing) return;
    // 직전까지의 대화를 history로(BE는 세션 미보관 → 클라가 전달)
    const history: CoachTurn[] = msgs.map((m) => ({
      role: m.role === 'bot' ? 'assistant' : 'user',
      content: m.text,
    }));
    setMsgs((m) => [...m, { role: 'user', text: t }]);
    setInput('');
    setErr(false);
    setTyping(true);
    void (async () => {
      try {
        const { reply } = await sendCoachingMessage(t, history, '다정한 건강냥');
        setMsgs((m) => [...m, { role: 'bot', text: reply || '음… 조금 더 들려줄래요?' }]);
      } catch {
        setErr(true);
        setMsgs((m) => [
          ...m,
          { role: 'bot', text: '건강냥이 아직 깨어나지 못했어요 (서버 연결을 확인해 주세요).' },
        ]);
      } finally {
        setTyping(false);
      }
    })();
  };

  const quick = ['잠이 안 와요', '오늘 끼니를 걸렀어요', '운동을 못 했어요', '약 먹는 걸 자꾸 잊어요'];

  return (
    <div className="screen">
      <div ref={scrollRef} className="screen-scroll" style={{ padding: 'calc(46px + var(--safe-t)) 14px calc(140px + var(--safe-b, 0px))' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 4 }}>
          <BackButton onClick={() => nav.back()} />
          <h1 className="h-title">밤 코칭 · 건강냥</h1>
        </div>
        <div className="tiny" style={{ marginBottom: 14 }}>
          밤에 깨어난 건강냥과 하루를 돌아봐요 · 진단·처방이 아닌 웰니스 코칭
        </div>

        <ChatThread msgs={msgs} typing={typing} avatar={COACH_AVATAR} />

        <h2 className="h-label" style={{ marginTop: 18, marginBottom: 6 }}>이야기 시작하기</h2>
        <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap' }}>
          {quick.map((t, i) => (
            <button
              key={i}
              type="button"
              onClick={() => send(t)}
              className="chip dashed chip-btn"
              style={{ background: 'transparent', border: '1.5px dashed var(--ink)' }}
            >
              {t}
            </button>
          ))}
        </div>

        {err && (
          <div className="tiny" role="alert" style={{ marginTop: 12, color: 'var(--danger)' }}>
            ⚠ 백엔드(건강냥이) 연결 실패 — <code>make up · migrate · be</code> 기동 후 다시 시도.
          </div>
        )}
      </div>

      <ChatInputRow
        value={input}
        onChange={setInput}
        onSend={() => send()}
        placeholder="건강냥에게 말 걸기..."
        ariaLabel="건강냥에게 말 걸기"
      />
      <TabBar active="home" />
    </div>
  );
};
