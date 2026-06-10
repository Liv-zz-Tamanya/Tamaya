import { useEffect, useRef, useState, type KeyboardEvent } from 'react';
import { StatusBar, TabBar } from '../components/primitives';
import { useNav } from '../lib/router';
import { sendHealthChat } from '../lib/api';

// S26 · 건강 RAG 챗 — 사용자 건강기록을 embedding 검색(top-5)해 컨텍스트로 답하는 헬스 Q&A.
// 건강냥이 BE: /api/v1/health-chat/sessions (+ /messages). 세션 기반(서버 보관).
// PII는 전송 직전 마스킹(liv-I1).

type Msg = { role: 'user' | 'bot'; text: string };

const INTRO: Msg = {
  role: 'bot',
  text: '내 건강 기록을 바탕으로 답해줄게요. 수면·식사·운동·복약 중 궁금한 걸 물어봐요.',
};

export const S26_HealthChat = () => {
  const nav = useNav();
  const [msgs, setMsgs] = useState<Msg[]>([INTRO]);
  const [input, setInput] = useState('');
  const [typing, setTyping] = useState(false);
  const [err, setErr] = useState(false);
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: 'smooth' });
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

  const onKey = (e: KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      send();
    }
  };

  const quick = ['요즘 수면 어때?', '이번 주 운동량은?', '식사 패턴 알려줘', '복약 잘 지켰어?'];

  return (
    <div className="phone-inner">
      <StatusBar mode="day" time="3:05 PM" />
      <div ref={scrollRef} className="phone-scroll" style={{ padding: '46px 14px 140px' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 4 }}>
          <span
            style={{ fontFamily: 'Caveat', fontSize: 22, cursor: 'pointer' }}
            onClick={() => nav.back()}
          >
            ‹
          </span>
          <div className="h-title">건강 기록 Q&amp;A</div>
        </div>
        <div className="tiny" style={{ marginBottom: 14 }}>
          내 건강 데이터(RAG) 기반 답변 · 진단 아님, 참고용
        </div>

        <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
          {msgs.map((m, i) =>
            m.role === 'bot' ? (
              <div key={i} style={{ display: 'flex', gap: 8, alignItems: 'flex-end' }}>
                <div className="ph-circle" style={{ width: 28, height: 28, fontSize: 11, flex: 'none' }}>✚</div>
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
              <div className="ph-circle" style={{ width: 28, height: 28, fontSize: 11, flex: 'none' }}>✚</div>
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

        {err && (
          <div className="tiny" style={{ marginTop: 12, color: '#8a2c33' }}>
            ⚠ 백엔드(건강냥이) 연결 실패 — 건강 기록 시드(<code>seed_demo_signals.py</code>) + 기동 확인.
          </div>
        )}
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
          placeholder="건강 기록에 대해 물어보기..."
          autoFocus
        />
        <button
          type="submit"
          className="btn primary"
          style={{ padding: 10, width: 42, height: 42, borderRadius: '50%', fontFamily: 'inherit', cursor: 'pointer', flex: 'none' }}
        >
          →
        </button>
      </form>
      <TabBar active="home" />
    </div>
  );
};
