import { useEffect, useRef, useState } from 'react';
import { BackButton, TabBar } from '../components/primitives';
import { ChatInputRow, ChatThread } from '../components/chat';
import { useNav } from '../lib/router';
import { scrollBehavior } from '../lib/scroll';
import { sendHealthChat } from '../lib/api';

// S26 · 건강 RAG 챗 — 사용자 건강기록을 embedding 검색(top-5)해 컨텍스트로 답하는 헬스 Q&A.
// 건강냥이 BE: /api/v1/health-chat/sessions (+ /messages). 세션 기반(서버 보관).
// PII는 전송 직전 마스킹(liv-I1).

type Msg = { role: 'user' | 'bot'; text: string };

const INTRO: Msg = {
  role: 'bot',
  text: '내 건강 기록을 바탕으로 답해줄게요. 수면·식사·운동·복약 중 궁금한 걸 물어봐요.',
};

const HEALTH_AVATAR = (
  <div className="ph-circle" style={{ width: 28, height: 28, fontSize: 11, flex: 'none' }}>✚</div>
);

export const S26_HealthChat = () => {
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
    setMsgs((m) => [...m, { role: 'user', text: t }]);
    setInput('');
    setErr(false);
    setTyping(true);
    void (async () => {
      try {
        const { reply } = await sendHealthChat(t);
        setMsgs((m) => [...m, { role: 'bot', text: reply || '관련 기록을 더 모아볼게요.' }]);
      } catch {
        setErr(true);
        setMsgs((m) => [
          ...m,
          { role: 'bot', text: '건강 기록을 불러오지 못했어요 (서버 연결을 확인해 주세요).' },
        ]);
      } finally {
        setTyping(false);
      }
    })();
  };

  const quick = ['요즘 수면 어때?', '이번 주 운동량은?', '식사 패턴 알려줘', '복약 잘 지켰어?'];

  return (
    <div className="screen">
      <div ref={scrollRef} className="screen-scroll" style={{ padding: 'calc(46px + var(--safe-t)) 14px calc(140px + var(--safe-b, 0px))' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 4 }}>
          <BackButton onClick={() => nav.back()} />
          <h1 className="h-title">건강 기록 Q&amp;A</h1>
        </div>
        <div className="tiny" style={{ marginBottom: 14 }}>
          내 건강 데이터(RAG) 기반 답변 · 진단 아님, 참고용
        </div>

        <ChatThread msgs={msgs} typing={typing} avatar={HEALTH_AVATAR} />

        <h2 className="h-label" style={{ marginTop: 18, marginBottom: 6 }}>자주 묻는 것</h2>
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
            ⚠ 백엔드(건강냥이) 연결 실패 — 건강 기록 시드(<code>seed_demo_signals.py</code>) + 기동 확인.
          </div>
        )}
      </div>

      <ChatInputRow
        value={input}
        onChange={setInput}
        onSend={() => send()}
        placeholder="건강 기록에 대해 물어보기..."
        ariaLabel="건강 기록에 대해 물어보기"
      />
      <TabBar active="home" />
    </div>
  );
};
