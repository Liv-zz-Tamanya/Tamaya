import { useState } from 'react';
import { CatSketch } from '../components/primitives';
import { useNav } from '../lib/router';
import { ApiError, checkNickname, loginWithNickname, signupWithNickname } from '../lib/api';

// 21 · 닉네임 입력 (데모: 비밀번호 없음)
// 진입 모드(signup/login)는 welcome 화면에서 setInitialAuthMode로 전달받는다.
//   - 회원가입 성공 → 온보딩(고양이 생성)으로
//   - 로그인 성공   → 바로 홈으로
// ⚠️ 비회원(익명) 진입 기능(ensureDeviceToken)은 유지하되 지금은 UI에서 노출하지 않음.

const NICK_MAX = 16;

type Mode = 'signup' | 'login';

// welcome → login 사이 모드 전달 (in-memory 라우터라 파라미터가 없어 모듈 변수로 넘긴다).
let initialMode: Mode = 'login';
export const setInitialAuthMode = (m: Mode) => {
  initialMode = m;
};

export const S21_Login = () => {
  const nav = useNav();
  // 마운트 시 1회 캡처 (이후 initialMode 변경과 무관).
  const [mode] = useState<Mode>(initialMode);
  const [nickname, setNickname] = useState('');
  const [loading, setLoading] = useState<'check' | 'submit' | null>(null);
  const [hint, setHint] = useState<{ ok: boolean; text: string } | null>(null);

  const busy = loading !== null;
  const isSignup = mode === 'signup';

  const doCheck = () => {
    const name = nickname.trim();
    if (!name) {
      setHint({ ok: false, text: '닉네임을 입력해 주세요' });
      return;
    }
    setLoading('check');
    void (async () => {
      try {
        const available = await checkNickname(name);
        setHint(
          available
            ? { ok: true, text: '사용 가능한 닉네임이에요' }
            : { ok: false, text: '이미 사용 중인 닉네임이에요' },
        );
      } catch {
        setHint({ ok: false, text: '확인 실패 · 서버 연결을 확인해 주세요' });
      } finally {
        setLoading(null);
      }
    })();
  };

  const submit = () => {
    const name = nickname.trim();
    if (!name) {
      setHint({ ok: false, text: '닉네임을 입력해 주세요' });
      return;
    }
    setLoading('submit');
    void (async () => {
      try {
        if (isSignup) {
          await signupWithNickname(name);
          nav.reset('privacy'); // 신규 → 온보딩(고양이 생성)으로
        } else {
          await loginWithNickname(name);
          nav.reset('home-night'); // 기존 → 바로 홈으로
        }
      } catch (e) {
        const status = e instanceof ApiError ? e.status : 0;
        if (isSignup && status === 409) {
          setHint({ ok: false, text: '이미 사용 중인 닉네임이에요' });
        } else if (!isSignup && status === 404) {
          setHint({ ok: false, text: '없는 닉네임이에요 · 회원가입해 주세요' });
        } else {
          setHint({ ok: false, text: '실패 · 서버 연결을 확인해 주세요' });
        }
        setLoading(null);
      }
    })();
  };

  return (
    <div
      className="screen"
      style={{
        background: 'linear-gradient(180deg, var(--paper) 0%, var(--paper-2) 70%, var(--accent-soft) 100%)',
      }}
    >
      <div
        className="screen-scroll"
        style={{
          padding: 'calc(60px + var(--safe-t)) 24px 24px',
          minHeight: '100%',
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          textAlign: 'center',
        }}
      >
        <div
          style={{
            background: 'var(--paper)',
            borderRadius: '50%',
            padding: 16,
            border: '2px solid var(--ink)',
            marginTop: 32,
          }}
        >
          <CatSketch size={100} mood="happy" />
        </div>
        <div className="h-display" style={{ fontSize: 40, marginTop: 14 }}>
          Tamaya
        </div>
        <div className="handwriting" style={{ fontSize: 19, marginTop: 4, color: 'var(--ink-soft)' }}>
          {isSignup ? '반가워요! 닉네임을 만들어 주세요' : '다시 왔군요! 닉네임을 알려주세요'}
        </div>

        <div style={{ marginTop: 'auto', width: '100%' }}>
          <div className="tiny" style={{ textAlign: 'left', color: 'var(--ink-soft)', marginBottom: 6 }}>
            {isSignup ? '회원가입 · 사용할 닉네임' : '로그인 · 닉네임'}
          </div>
          <div style={{ display: 'flex', gap: 8 }}>
            <input
              id="nickname"
              type="text"
              value={nickname}
              maxLength={NICK_MAX}
              disabled={busy}
              autoFocus
              placeholder={`닉네임 (최대 ${NICK_MAX}자)`}
              aria-label={isSignup ? '회원가입 · 사용할 닉네임' : '로그인 · 닉네임'}
              onChange={(e) => {
                setNickname(e.target.value);
                setHint(null);
              }}
              onKeyDown={(e) => {
                if (e.key === 'Enter') submit();
              }}
              style={{
                flex: 1,
                minWidth: 0,
                padding: '12px 14px',
                borderRadius: 12,
                border: '1.5px solid var(--ink)',
                background: 'var(--bg)',
                color: 'var(--ink)',
                fontFamily: 'inherit',
                fontSize: 16,
              }}
            />
            {isSignup && (
              <button
                type="button"
                disabled={busy}
                onClick={doCheck}
                className="btn"
                style={{
                  flexShrink: 0,
                  background: 'var(--bg)',
                  color: 'var(--ink)',
                  border: '1.5px solid var(--ink)',
                  cursor: busy ? 'wait' : 'pointer',
                  fontFamily: 'inherit',
                  padding: '0 14px',
                }}
              >
                {loading === 'check' ? '…' : '중복확인'}
              </button>
            )}
          </div>

          {hint && (
            <div
              className="tiny"
              style={{
                marginTop: 8,
                textAlign: 'left',
                color: hint.ok ? '#2e7d32' : '#b3261e',
              }}
            >
              {hint.text}
            </div>
          )}

          <button
            type="button"
            disabled={busy}
            onClick={submit}
            className="btn primary block"
            style={{ marginTop: 14, cursor: busy ? 'wait' : 'pointer', fontFamily: 'inherit' }}
          >
            {loading === 'submit' ? '잠시만요…' : isSignup ? '회원가입' : '로그인'}
          </button>
          <button
            type="button"
            disabled={busy}
            onClick={() => nav.back()}
            style={{
              marginTop: 12,
              background: 'none',
              border: 'none',
              color: 'var(--ink-soft)',
              textDecoration: 'underline',
              cursor: busy ? 'wait' : 'pointer',
              fontFamily: 'inherit',
              fontSize: 13,
            }}
          >
            ← 뒤로
          </button>
        </div>
      </div>
    </div>
  );
};
