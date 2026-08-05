import { CSSProperties, ReactNode, RefObject, useEffect, useRef } from 'react';

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

// 자동 확장 채팅 입력란 — 내용이 줄바꿈되면 세로로 자라 사용자가 쓴 내용을 다 볼 수 있다.
// (가로는 화면폭이 상한이라 줄바꿈으로 확장 — 최대 4줄, 이후 내부 스크롤은 CSS max-height.)
// Enter(shift 제외) 전송, Shift+Enter 줄바꿈. 한글 IME 조합 중 Enter 는 무시(조기 전송 방지).
// 값이 비워지면(전송 직후) 1줄 높이로 복귀. inputRef 는 화면에서 재포커스가 필요할 때 주입.
export const GrowingChatTextarea = ({
  value,
  onChange,
  onSubmit,
  placeholder,
  ariaLabel,
  disabled,
  inputRef,
}: {
  value: string;
  onChange: (v: string) => void;
  onSubmit: () => void;
  placeholder: string;
  ariaLabel: string;
  disabled?: boolean;
  inputRef?: RefObject<HTMLTextAreaElement>;
}) => {
  const innerRef = useRef<HTMLTextAreaElement>(null);
  const ref = inputRef ?? innerRef;

  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    // scrollHeight 재측정을 위해 높이를 풀었다가 다시 잰다. +3 = 상하 border(1.5px×2).
    el.style.height = 'auto';
    el.style.height = `${el.scrollHeight + 3}px`; // 상한(4줄)은 CSS max-height 가 잡는다
  }, [value, ref]);

  return (
    <textarea
      ref={ref}
      rows={1}
      value={value}
      onChange={(e) => onChange(e.target.value)}
      onKeyDown={(e) => {
        if (e.key === 'Enter' && !e.shiftKey && !e.nativeEvent.isComposing) {
          e.preventDefault();
          onSubmit();
        }
      }}
      placeholder={placeholder}
      aria-label={ariaLabel}
      disabled={disabled}
      autoFocus
    />
  );
};

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
}) => (
  <form
    onSubmit={(e) => {
      e.preventDefault();
      onSend();
    }}
    className="input-row above-tabbar"
  >
    <GrowingChatTextarea
      value={value}
      onChange={onChange}
      onSubmit={onSend}
      placeholder={placeholder}
      ariaLabel={ariaLabel}
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
