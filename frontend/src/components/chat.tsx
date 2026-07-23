import { CSSProperties, KeyboardEvent, ReactNode } from 'react';

// 공용 챗 스캐폴드 — coach·health-chat·S09 AIChat·S11 ChatDiary 의 스레드 렌더가
// 사실상 동일해 발생하던 4중 복제를 제거(Q5). 각 화면 고유 요소(아바타·엔드포인트·
// quick 칩·에러 폴백)는 화면에 남기고, 반복되는 메시지 버블 컬럼 + 타이핑 인디케이터
// (스레드)와 입력바만 공용화한다. 무리한 통합 금지 — 회귀 우선(S11 입력바는 고유 유지).

export type ChatThreadMsg = { role: 'user' | 'bot'; text: string; hint?: string };

// 스레드 — bot/user 버블 컬럼 + 타이핑 도트. avatar 는 bot 행·타이핑 행에 같은 노드로
// 들어간다(화면별 아바타 차이를 prop 으로 흡수). style 은 컨테이너에 병합(S11 marginTop).
export const ChatThread = ({
  msgs,
  typing,
  avatar,
  style,
}: {
  msgs: ChatThreadMsg[];
  typing: boolean;
  avatar: ReactNode;
  style?: CSSProperties;
}) => (
  <div style={{ display: 'flex', flexDirection: 'column', gap: 10, ...style }}>
    {msgs.map((m, i) =>
      m.role === 'bot' ? (
        <div key={i} style={{ display: 'flex', gap: 8, alignItems: 'flex-end' }}>
          {avatar}
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
        {avatar}
        <div className="bubble bubble-bot" style={{ padding: '12px 16px' }}>
          <span className="typing-dot" />
          <span className="typing-dot" />
          <span className="typing-dot" />
        </div>
      </div>
    )}
  </div>
);

// 입력바 — coach·health-chat·S09 공용(input-row above-tabbar + btn primary 42px 원형 →).
// Enter(shift 제외) 전송. aria-label 보존(T9). onSend 는 인자 없이 호출 → 화면의
// send() 가 현재 input 값을 사용(quick 칩은 화면에서 send(t) 로 직접 호출).
export const ChatInputRow = ({
  value,
  onChange,
  onSend,
  placeholder,
  ariaLabel,
}: {
  value: string;
  onChange: (v: string) => void;
  onSend: () => void;
  placeholder: string;
  ariaLabel: string;
}) => {
  const onKey = (e: KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      onSend();
    }
  };
  return (
    <form
      onSubmit={(e) => {
        e.preventDefault();
        onSend();
      }}
      className="input-row above-tabbar"
    >
      <input
        value={value}
        onChange={(e) => onChange(e.target.value)}
        onKeyDown={onKey}
        placeholder={placeholder}
        aria-label={ariaLabel}
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
  );
};
