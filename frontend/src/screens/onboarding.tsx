import { CSSProperties, useEffect, useState } from 'react';
import { CatSketch } from '../components/primitives';
import { useNav } from '../lib/router';
import { CatColor, Personality, useStore } from '../lib/store';
import { setInitialAuthMode } from './login';

// 01-05 · Onboarding sequence (5 screens) — v4 Figma Section1 시각 언어 적용
// 로직(핸들러·nav·store)은 불변. 마크업/스타일/정적 문구만 v4로 번역.

// v4 온보딩 4단계 진행 인디케이터 (S02~S05 공용). 순수 표현 요소.
const OnbProgress = ({
  step,
  dark = false,
  style,
}: {
  step: number;
  dark?: boolean;
  style?: CSSProperties;
}) => (
  <div style={{ display: 'flex', gap: 6, width: '100%', maxWidth: 240, ...style }} aria-hidden="true">
    {[1, 2, 3, 4].map((i) => {
      const on = i <= step;
      const line = dark ? 'var(--accent-soft)' : 'var(--ink)';
      return (
        <div
          key={i}
          style={{
            flex: 1,
            height: 6,
            borderRadius: 999,
            border: '0.5px solid ' + (on ? line : dark ? 'var(--pencil)' : 'var(--muted)'),
            background: on ? line : 'transparent',
          }}
        />
      );
    })}
  </div>
);

export const S01_Splash = () => {
  const nav = useNav();
  // Auto-advance after 1.5s — match the design intent (splash → welcome).
  useEffect(() => {
    const t = setTimeout(() => nav.go('welcome'), 1500);
    return () => clearTimeout(t);
  }, [nav]);
  return (
  <div className="screen" style={{ background: 'var(--night)', color: 'var(--paper)' }}>
    <svg width="100%" height="100%" style={{ position: 'absolute', inset: 0, opacity: 0.5 }}>
      {[
        [40, 90],
        [120, 60],
        [300, 80],
        [260, 180],
        [60, 220],
        [330, 220],
        [180, 140],
        [80, 400],
        [300, 420],
        [330, 520],
        [40, 560],
        [160, 640],
      ].map(([x, y], i) => (
        <g key={i}>
          <circle cx={x} cy={y} r="1.5" fill="#f5e6cf" />
          {i % 3 === 0 && (
            <path
              d={`M${x - 4} ${y} L${x + 4} ${y} M${x} ${y - 4} L${x} ${y + 4}`}
              stroke="#f5e6cf"
              strokeWidth="0.5"
            />
          )}
        </g>
      ))}
    </svg>
    <div
      style={{
        position: 'absolute',
        inset: 0,
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center',
        gap: 26,
      }}
    >
      <div
        style={{
          background: 'var(--paper-3)',
          borderRadius: '50%',
          padding: 18,
          border: '2px solid var(--ink)',
        }}
      >
        <CatSketch size={128} mood="wink" />
      </div>
      <div style={{ textAlign: 'center' }}>
        <div className="h-display" style={{ fontSize: 52, color: 'var(--paper)' }}>
          Tamaya
        </div>
        <div className="handwriting" style={{ color: 'var(--accent-soft)', marginTop: 8 }}>
          밤이 되면 만나요
        </div>
      </div>
      <div className="tiny" style={{ color: 'var(--accent-soft)', position: 'absolute', bottom: 'calc(36px + var(--safe-b, 0px))' }}>
        · · ·
      </div>
    </div>
  </div>
  );
};

export const S02_Welcome = () => {
  const nav = useNav();
  return (
  <div className="screen">
    <div className="screen-scroll" style={{ padding: '56px 24px 120px' }}>
      <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
        <div className="h-section">01 / 04 · 인사</div>
        <OnbProgress step={1} />
        <div className="h-display" style={{ fontSize: 28, lineHeight: 1.15 }}>
          혼자여도
          <br />
          외롭지 않게.
        </div>
        <div className="body" style={{ color: 'var(--ink)', lineHeight: 1.55 }}>
          하루를 더 잘 준비하고
          <br />
          마무리할 수 있도록
          <br />
          이음이가 매일 밤 곁에 있어줘요.
        </div>
      </div>
      <div style={{ marginTop: 28, display: 'flex', justifyContent: 'center' }}>
        <div
          className="hbox"
          style={{
            width: 260,
            padding: 20,
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
            gap: 14,
          }}
        >
          <CatSketch size={150} />
          <div className="handwriting" style={{ textAlign: 'center', fontSize: 20, color: 'var(--ink)' }}>
            "안녕, 나는 이음이야
            <br />
            만나서 반가워"
          </div>
        </div>
      </div>
    </div>
    <div style={{ position: 'absolute', bottom: 'calc(24px + var(--safe-b, 0px))', left: 24, right: 24 }}>
      <button
        type="button"
        onClick={() => {
          setInitialAuthMode('signup');
          nav.go('login');
        }}
        className="btn primary block"
        style={{ cursor: 'pointer', fontFamily: 'inherit' }}
      >
        시작하기
      </button>
      <button
        type="button"
        onClick={() => {
          setInitialAuthMode('login');
          nav.go('login');
        }}
        className="btn ghost block"
        style={{
          marginTop: 8,
          fontSize: 12,
          color: 'var(--pencil)',
          boxShadow: 'none',
          border: 'none',
          cursor: 'pointer',
          fontFamily: 'inherit',
        }}
      >
        이미 계정이 있어요 → 로그인
      </button>
    </div>
  </div>
  );
};

export const S03_Privacy = () => {
  const nav = useNav();
  return (
  <div className="screen">
    <div className="screen-scroll" style={{ padding: '52px 24px 120px' }}>
      <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
        <div className="h-section">02 / 04 · 약속</div>
        <OnbProgress step={2} />
        <div className="h-display" style={{ fontSize: 28, lineHeight: 1.15 }}>
          네 마음은
          <br />
          너만의 것이야.
        </div>
      </div>
      <div style={{ marginTop: 20, display: 'flex', flexDirection: 'column', gap: 10 }}>
        {(
          [
            ['◐', '대화 속 개인정보는 지운 뒤에만 AI에게 전달돼요', ''],
            ['☷', '일기는 내 계정에만 — 다른 곳에 팔거나 공유하지 않아요', ''],
            ['⌧', '언제든 서버·기기에서 완전 삭제할 수 있어요', ''],
          ] as [string, string, string][]
        ).map(([ic, t, s], i) => (
          <div
            key={i}
            className="hbox"
            style={{ display: 'flex', alignItems: 'center', gap: 12, padding: '11px 14px' }}
          >
            <div
              className="ph-circle"
              style={{ width: 40, height: 40, flex: 'none', fontFamily: 'Pretendard', fontSize: 18 }}
            >
              {ic}
            </div>
            <div style={{ flex: 1, minWidth: 0 }}>
              <div style={{ fontFamily: 'Pretendard', fontSize: 15, fontWeight: 600 }}>{t}</div>
              <div
                className="tiny"
                style={{
                  color: 'var(--muted)',
                  whiteSpace: 'nowrap',
                  overflow: 'hidden',
                  textOverflow: 'ellipsis',
                }}
              >
                {s}
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
    <div style={{ position: 'absolute', bottom: 'calc(28px + var(--safe-b, 0px))', left: 24, right: 24 }}>
      <button
        type="button"
        onClick={() => nav.go('create-cat')}
        className="btn primary block"
        style={{ cursor: 'pointer', fontFamily: 'inherit' }}
      >
        알겠어요
      </button>
    </div>
  </div>
  );
};

export const S04_CreateCat = () => {
  const nav = useNav();
  const { state, dispatch } = useStore();
  const [name, setName] = useState(state.character.name);
  // CatColor = 사용자 선택 데이터(store 영속·타입 리터럴) — 디자인 토큰 아님, hex 리터럴 유지
  const colors: CatColor[] = ['#f5e6cf', '#d8a777', '#a66838', '#6b3e1f', '#3a2414'];
  const allPersonalities: Personality[] = ['차분한', '수다쟁이', '시크', '다정한', '장난꾸러기'];

  const togglePersonality = (p: Personality) => {
    const have = state.character.personalities.includes(p);
    const next = have
      ? state.character.personalities.filter((x) => x !== p)
      : [...state.character.personalities, p].slice(0, 2); // max 2
    dispatch({ type: 'character/set', patch: { personalities: next } });
  };

  const save = () => {
    dispatch({ type: 'character/set', patch: { name: name.trim() || '이음이' } });
    nav.go('first-meet');
  };

  return (
  <div className="screen">
    <div className="screen-scroll" style={{ padding: '48px 24px 120px' }}>
      <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
        <div className="h-section">03 / 04 · 캐릭터</div>
        <OnbProgress step={3} />
        <div className="h-display" style={{ fontSize: 28, lineHeight: 1.15 }}>
          너만의 이음이를
          <br />
          만들어 봐.
        </div>
      </div>

      <div
        className="hbox"
        style={{
          marginTop: 18,
          padding: 18,
          display: 'flex',
          justifyContent: 'center',
        }}
      >
        <CatSketch size={130} mood="happy" color="#3a2414" accent={state.character.color} />
      </div>

      <input
        value={name}
        onChange={(e) => setName(e.target.value)}
        maxLength={10}
        placeholder="이음이에게 이름을 지어 주세요..."
        style={{
          marginTop: 12,
          width: '100%',
          border: '1.5px solid var(--ink)',
          borderRadius: 999,
          padding: '11px 16px',
          background: 'var(--paper)',
          fontFamily: 'Pretendard',
          fontSize: 15,
          color: 'var(--ink)',
          outline: 'none',
        }}
      />

      <div className="h-label" style={{ marginTop: 18, marginBottom: 8 }}>
        털 색 고르기
      </div>
      <div style={{ display: 'flex', gap: 10 }}>
        {colors.map((c) => {
          const selected = state.character.color === c;
          return (
            <button
              key={c}
              type="button"
              onClick={() => dispatch({ type: 'character/set', patch: { color: c } })}
              className="ph-circle"
              style={{
                width: 36,
                height: 36,
                background: c,
                border: selected ? '3px solid var(--accent)' : '1.5px solid var(--ink)',
                cursor: 'pointer',
                padding: 0,
              }}
            />
          );
        })}
      </div>

      <div className="h-label" style={{ marginTop: 18, marginBottom: 8 }}>
        성격 (말투에 영향) · 최대 2개
      </div>
      <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
        {allPersonalities.map((t) => {
          const on = state.character.personalities.includes(t);
          return (
            <button
              key={t}
              type="button"
              onClick={() => togglePersonality(t)}
              className={'chip chip-btn ' + (on ? 'accent' : '')}
            >
              {t}
            </button>
          );
        })}
      </div>

      <div className="tiny" style={{ marginTop: 14, color: 'var(--muted)' }}>
        나중에 [설정]에서 언제든 바꿀 수 있어요.
      </div>
    </div>
    <div style={{ position: 'absolute', bottom: 'calc(28px + var(--safe-b, 0px))', left: 24, right: 24 }}>
      <button
        type="button"
        onClick={save}
        className="btn primary block"
        style={{ cursor: 'pointer', fontFamily: 'inherit' }}
      >
        다음
      </button>
    </div>
  </div>
  );
};

export const S05_FirstMeet = () => {
  const nav = useNav();
  const { state } = useStore();
  const name = state.character.name || '이음이';
  return (
  <div className="screen" style={{ background: 'var(--night)', color: 'var(--paper)' }}>
    <svg width="100%" height="180" style={{ position: 'absolute', top: 40, opacity: 0.4 }}>
      {[
        [60, 40],
        [140, 80],
        [260, 50],
        [320, 110],
        [100, 140],
        [200, 30],
      ].map(([x, y], i) => (
        <circle key={i} cx={x} cy={y} r="1.5" fill="#f5e6cf" />
      ))}
    </svg>
    <div className="screen-scroll" style={{ padding: '56px 24px 120px' }}>
      <div style={{ display: 'flex', flexDirection: 'column', gap: 14, alignItems: 'center', textAlign: 'center' }}>
        <div className="h-section" style={{ color: 'var(--accent-soft)' }}>
          04 / 04 · 첫 만남
        </div>
        <OnbProgress step={4} dark style={{ marginInline: 'auto' }} />
        <div className="h-display" style={{ fontSize: 28, lineHeight: 1.15, color: 'var(--paper)' }}>
          이제 만났네,
          <br />
          {name}!
        </div>
      </div>

      <div style={{ marginTop: 30, display: 'flex', justifyContent: 'center' }}>
        <div
          style={{
            background: 'var(--paper)',
            borderRadius: 14,
            border: '1.5px solid var(--ink)',
            padding: 14,
            display: 'flex',
          }}
        >
          <CatSketch size={150} mood="wink" />
        </div>
      </div>

      <div
        className="handwriting"
        style={{ marginTop: 22, textAlign: 'center', fontSize: 18, color: 'var(--accent-soft)' }}
      >
        "안녕, 난 {name}. 너의 밤 친구야."
      </div>
    </div>
    <div style={{ position: 'absolute', bottom: 'calc(28px + var(--safe-b, 0px))', left: 24, right: 24 }}>
      <button
        type="button"
        onClick={() => nav.reset('home-night')}
        className="btn primary block"
        style={{ cursor: 'pointer', fontFamily: 'inherit' }}
      >
        홈으로
      </button>
    </div>
    <div
      style={{ position: 'absolute', bottom: 'calc(8px + var(--safe-b, 0px))', left: 24, right: 24, textAlign: 'center' }}
    >
      <div className="tiny" style={{ color: 'var(--accent-soft)' }}>
        이제부터 매일 밤 만나요
      </div>
    </div>
  </div>
  );
};
