import { useEffect, useState } from 'react';
import { CatSketch, StatusBar } from '../components/primitives';
import { useNav } from '../lib/router';
import { CatColor, Personality, useStore } from '../lib/store';

// 01-05 · Onboarding sequence (5 screens, 375×812)

export const S01_Splash = () => {
  const nav = useNav();
  // Auto-advance after 1.5s — match the design intent (splash → welcome).
  useEffect(() => {
    const t = setTimeout(() => nav.go('welcome'), 1500);
    return () => clearTimeout(t);
  }, [nav]);
  return (
  <div
    className="phone-inner"
    style={{
      background: 'linear-gradient(180deg, #4a2f1e 0%, #2b1810 100%)',
      color: '#f5e6cf',
    }}
  >
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
        gap: 24,
      }}
    >
      <div
        style={{
          background: '#f5e6cf',
          borderRadius: '50%',
          padding: 18,
          border: '2px solid #3a2414',
        }}
      >
        <CatSketch size={120} mood="wink" />
      </div>
      <div style={{ textAlign: 'center' }}>
        <div className="h-display" style={{ fontSize: 48, color: '#f5e6cf' }}>
          Tamaya
        </div>
        <div className="handwriting" style={{ color: '#d8a777', marginTop: 6 }}>
          밤이 되면 만나요
        </div>
      </div>
      <div className="tiny" style={{ color: '#d8a777', position: 'absolute', bottom: 36 }}>
        · · ·
      </div>
    </div>
  </div>
  );
};

export const S02_Welcome = () => {
  const nav = useNav();
  return (
  <div className="phone-inner">
    <StatusBar mode="day" time="9:24 AM" />
    <div className="phone-scroll" style={{ padding: '60px 24px 100px' }}>
      <div className="h-section">01 / 04 — Welcome</div>
      <div className="h-display" style={{ marginTop: 14, fontSize: 38 }}>
        혼자여도
        <br />
        외롭지 않게.
      </div>
      <div className="body" style={{ marginTop: 18, color: '#3a342c', lineHeight: 1.5 }}>
        1인 가구의 하루를 더 잘 준비하고
        <br />
        마무리할 수 있도록 — 작은 고양이가
        <br />
        매일 밤 곁에 있어줘요.
      </div>
      <div style={{ marginTop: 32, display: 'flex', justifyContent: 'center' }}>
        <div
          className="hbox"
          style={{
            width: 260,
            height: 300,
            padding: 16,
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
            justifyContent: 'center',
            gap: 14,
          }}
        >
          <CatSketch size={160} />
          <div className="handwriting" style={{ whiteSpace: 'nowrap', fontSize: 22 }}>
            "안녕, 친구 ☾"
          </div>
        </div>
      </div>
    </div>
    <div style={{ position: 'absolute', bottom: 28, left: 24, right: 24 }}>
      <button
        type="button"
        onClick={() => nav.go('privacy')}
        className="btn primary block"
        style={{ cursor: 'pointer', fontFamily: 'inherit' }}
      >
        시작하기
      </button>
    </div>
    <div
      style={{ position: 'absolute', bottom: 8, left: 24, right: 24, textAlign: 'center' }}
    >
      <button
        type="button"
        onClick={() => nav.go('login')}
        className="tiny"
        style={{
          background: 'transparent',
          border: 'none',
          cursor: 'pointer',
          fontFamily: 'inherit',
          color: '#7a5634',
          textDecoration: 'underline',
        }}
      >
        이미 계정이 있어요  →  로그인
      </button>
    </div>
  </div>
  );
};

export const S03_Privacy = () => {
  const nav = useNav();
  return (
  <div className="phone-inner">
    <StatusBar mode="day" time="9:24 AM" />
    <div className="phone-scroll" style={{ padding: '52px 24px 100px' }}>
      <div className="h-section">02 / 04 — 약속</div>
      <div className="h-display" style={{ marginTop: 12, fontSize: 30 }}>
        네 마음은
        <br />
        너만의 것이야.
      </div>
      <div className="body" style={{ marginTop: 14, color: '#3a342c' }}>
        일기와 감정 기록은 기기 안에 머물러요.
        <br />
        네가 원할 때만 백업할 수 있어요.
      </div>
      <div style={{ marginTop: 22, display: 'flex', flexDirection: 'column', gap: 10 }}>
        {(
          [
            ['◐', '로컬 우선 저장', '일기·감정은 기기 안에'],
            ['☷', '익명 분석', '내용은 학습에 쓰지 않음'],
            ['⌧', '언제든 삭제', '한 번에 모든 기록 지우기'],
          ] as [string, string, string][]
        ).map(([ic, t, s], i) => (
          <div
            key={i}
            className={'hbox r-' + (i % 2 ? 'r' : 'l')}
            style={{ display: 'flex', alignItems: 'center', gap: 12, padding: '12px 14px' }}
          >
            <div
              className="ph-circle"
              style={{ width: 36, height: 36, flex: 'none', fontFamily: 'Patrick Hand' }}
            >
              {ic}
            </div>
            <div style={{ flex: 1, minWidth: 0 }}>
              <div style={{ fontFamily: 'Patrick Hand', fontWeight: 700 }}>{t}</div>
              <div
                className="tiny"
                style={{
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
      <div className="sticky" style={{ marginTop: 18, transform: 'rotate(-1.5deg)' }}>
        ※ 기기 분실 시 복구 불가 — 백업 권장
      </div>
    </div>
    <div style={{ position: 'absolute', bottom: 28, left: 24, right: 24 }}>
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
  <div className="phone-inner">
    <StatusBar mode="day" time="9:25 AM" />
    <div className="phone-scroll" style={{ padding: '52px 24px 100px' }}>
      <div className="h-section">03 / 04 — 캐릭터 만들기</div>
      <div className="h-display" style={{ marginTop: 12, fontSize: 30 }}>
        너만의 집사를
        <br />
        지어줘.
      </div>

      <div
        className="hbox r-l"
        style={{
          marginTop: 18,
          padding: 18,
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          gap: 8,
        }}
      >
        <CatSketch
          size={120}
          mood="happy"
          color="#3a2414"
          accent={state.character.color}
        />
        <input
          value={name}
          onChange={(e) => setName(e.target.value)}
          maxLength={10}
          placeholder="이름 (최대 10자)"
          style={{
            border: '1.5px dashed #3a2414',
            borderRadius: 8,
            padding: '6px 14px',
            background: 'transparent',
            fontFamily: 'Caveat',
            fontSize: 22,
            color: '#3a2414',
            textAlign: 'center',
            width: 160,
            outline: 'none',
          }}
        />
      </div>

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
                border: selected ? '3px solid #8c4a1f' : '1.5px solid #3a2414',
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

      <div className="tiny" style={{ marginTop: 14 }}>
        나중에 [설정]에서 언제든 바꿀 수 있어요.
      </div>
    </div>
    <div style={{ position: 'absolute', bottom: 28, left: 24, right: 24 }}>
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
  return (
  <div
    className="phone-inner"
    style={{
      background: 'linear-gradient(180deg, #4a2f1e 0%, #1a0e08 100%)',
      color: '#f5e6cf',
    }}
  >
    <StatusBar mode="night" time="10:18 PM" />
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
    <div className="phone-scroll" style={{ padding: '60px 24px 100px' }}>
      <div className="h-section" style={{ color: '#d8a777' }}>
        04 / 04 — 첫 만남
      </div>
      <div className="h-display" style={{ marginTop: 14, color: '#f5e6cf' }}>
        밤 10시 18분.
        <br />
        나, 이제 깨어났어.
      </div>

      <div style={{ marginTop: 28, display: 'flex', justifyContent: 'center' }}>
        <div
          style={{
            background: '#f5e6cf',
            borderRadius: 16,
            border: '2px solid #3a2414',
            padding: 14,
            transform: 'rotate(-2deg)',
          }}
        >
          <CatSketch size={140} mood="wink" />
        </div>
      </div>

      <div
        style={{
          marginTop: 24,
          padding: '14px 16px',
          background: 'rgba(251,248,243,0.95)',
          color: '#3a2414',
          border: '1.5px solid #3a2414',
          borderRadius: 14,
          position: 'relative',
        }}
      >
        <div className="handwriting" style={{ fontSize: 20 }}>
          "안녕. 난 너의 밤 친구야.
          <br />
          낮엔 자고 — 밤이 되면 같이 오늘을 정리해."
        </div>
        <svg
          style={{ position: 'absolute', left: 30, bottom: -10 }}
          width="20"
          height="14"
          viewBox="0 0 20 14"
        >
          <path d="M0 0 L 10 12 L 20 0 Z" fill="#f5e6cf" stroke="#3a2414" strokeWidth="1.5" />
        </svg>
      </div>
    </div>
    <div style={{ position: 'absolute', bottom: 28, left: 24, right: 24 }}>
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
      style={{ position: 'absolute', bottom: 8, left: 24, right: 24, textAlign: 'center' }}
    >
      <div className="tiny" style={{ color: '#d8a777' }}>
        이제부터 매일 밤 만나요
      </div>
    </div>
  </div>
  );
};
