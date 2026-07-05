import { useEffect, useRef, useState, type KeyboardEvent } from 'react';
import { TabBar } from '../components/primitives';
import { useNav } from '../lib/router';
import { sendCoachingMessage, type CoachTurn } from '../lib/api';

// S23 · 밤 코칭 (건강냥 Medlife) — guardrail-first 코칭 대화.
// 건강냥이 BE: POST /api/v1/coaching/messages (stateless, 클라가 history 보관).
// 의료 요구는 BE에서 면책으로 단락된다. PII는 전송 직전 마스킹(liv-I1).

type Msg = { role: 'user' | 'bot'; text: string };

const INTRO: Msg = {
  role: 'bot',
  text: '오늘 하루도 고생 많았어요. 잠들기 전에, 몸이나 마음 중 뭐가 제일 신경 쓰여요?',
};

// 와이어프레임 캔버스(#design)용 샘플 대화 — 백엔드 없이 채워진 상태를 보여준다.
const SAMPLE_MSGS: Msg[] = [
  INTRO,
  { role: 'user', text: '요즘 잠들기가 너무 어려워요.' },
  {
    role: 'bot',
    text: '잠들기 어려운 밤이 이어지면 참 지치죠. 잠들기 한 시간 전엔 화면을 멀리하고, 매일 비슷한 시각에 눕는 작은 리듬부터 만들어볼까요? (진단이 아니라 함께 찾는 습관이에요.)',
  },
];

export const S23_Coach = ({ sample = false }: { sample?: boolean } = {}) => {
  const nav = useNav();
  const [msgs, setMsgs] = useState<Msg[]>(sample ? SAMPLE_MSGS : [INTRO]);
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
    if (sample) {
      // 와이어프레임 캔버스 — 네트워크 호출 없이 예시 응답만.
      setMsgs((m) => [...m, { role: 'user', text: t }, { role: 'bot', text: '(예시 모드) 실제 코칭은 건강냥 백엔드 연결 후 동작해요.' }]);
      setInput('');
      return;
    }
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

  const onKey = (e: KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      send();
    }
  };

  const quick = ['잠이 안 와요', '오늘 끼니를 걸렀어요', '운동을 못 했어요', '약 먹는 걸 자꾸 잊어요'];

  return (
    <div className="phone-inner">
      <div ref={scrollRef} className="phone-scroll" style={{ padding: '46px 14px calc(140px + var(--safe-b, 0px))' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 4 }}>
          <span
            style={{ fontFamily: 'Pretendard', fontSize: 22, cursor: 'pointer' }}
            onClick={() => nav.back()}
          >
            ‹
          </span>
          <div className="h-title">밤 코칭 · 건강냥</div>
        </div>
        <div className="tiny" style={{ marginBottom: 14 }}>
          밤에 깨어난 건강냥과 하루를 돌아봐요 · 진단·처방이 아닌 웰니스 코칭
        </div>

        <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
          {msgs.map((m, i) =>
            m.role === 'bot' ? (
              <div key={i} style={{ display: 'flex', gap: 8, alignItems: 'flex-end' }}>
                <div className="ph-circle" style={{ width: 28, height: 28, flex: 'none', overflow: 'hidden' }}><img src="/character/head-glasses.png" alt="건강냥" style={{ width: '100%', height: '100%', objectFit: 'contain' }} draggable={false} /></div>
                <div className="bubble bubble-bot">
                  <div className="body" style={{ whiteSpace: 'pre-wrap' }}>{m.text}</div>
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
              <div className="ph-circle" style={{ width: 28, height: 28, flex: 'none', overflow: 'hidden' }}><img src="/character/head-glasses.png" alt="건강냥" style={{ width: '100%', height: '100%', objectFit: 'contain' }} draggable={false} /></div>
              <div className="bubble bubble-bot" style={{ padding: '12px 16px' }}>
                <span className="typing-dot" />
                <span className="typing-dot" />
                <span className="typing-dot" />
              </div>
            </div>
          )}
        </div>

        <div className="h-label" style={{ marginTop: 18, marginBottom: 6 }}>이야기 시작하기</div>
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
            ⚠ 백엔드(건강냥이) 연결 실패 — <code>make up · migrate · be</code> 기동 후 다시 시도.
          </div>
        )}
      </div>

      <form
        onSubmit={(e) => {
          e.preventDefault();
          send();
        }}
        className="input-row above-tabbar"
      >
        <input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={onKey}
          placeholder="건강냥에게 말 걸기..."
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
