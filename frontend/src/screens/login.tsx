import { useState, type CSSProperties, type KeyboardEvent } from 'react';
import { CatSketch } from '../components/primitives';
import { useNav } from '../lib/router';
import { ApiError, checkNickname, loginWithNickname, signupWithNickname } from '../lib/api';

// 21 · 닉네임 + 비밀번호 입력
// 진입 모드(signup/login)는 welcome 화면에서 setInitialAuthMode로 전달받는다.
//   - 회원가입 성공 → 온보딩(고양이 생성)으로
//   - 로그인 성공   → 바로 홈으로
// ⚠️ 비회원(익명) 진입 기능(ensureDeviceToken)은 유지하되 지금은 UI에서 노출하지 않음.

const NICK_MAX = 16;
const PW_MIN = 4;
const PW_MAX = 64;

type Mode = 'signup' | 'login';

// welcome → login 사이 모드 전달 (in-memory 라우터라 파라미터가 없어 모듈 변수로 넘긴다).
let initialMode: Mode = 'login';
export const setInitialAuthMode = (m: Mode) => {
  initialMode = m;
};

const inputStyle: CSSProperties = {
  flex: 1,
  minWidth: 0,
  padding: '12px 14px',
  borderRadius: 12,
  border: '1.5px solid var(--ink)',
  background: 'var(--bg)',
  color: 'var(--ink)',
  fontFamily: 'inherit',
  fontSize: 16,
};

const labelStyle: CSSProperties = {
  textAlign: 'left',
  color: 'var(--ink-soft)',
  marginBottom: 6,
};

export const S21_Login = () => {
  const nav = useNav();
  // 마운트 시 1회 캡처 (이후 initialMode 변경과 무관).
  const [mode] = useState<Mode>(initialMode);
  const [nickname, setNickname] = useState('');
  const [password, setPassword] = useState('');
  const [passwordConfirm, setPasswordConfirm] = useState('');
  const [loading, setLoading] = useState<'check' | 'submit' | null>(null);
  const [hint, setHint] = useState<{ ok: boolean; text: string } | null>(null);

  const busy = loading !== null;
  const isSignup = mode === 'signup';

  const clearHint = () => setHint(null);

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
    if (password.length < PW_MIN) {
      setHint({ ok: false, text: `비밀번호는 ${PW_MIN}자 이상이어야 해요` });
      return;
    }
    if (isSignup && password !== passwordConfirm) {
      setHint({ ok: false, text: '비밀번호가 서로 달라요 · 다시 확인해 주세요' });
      return;
    }
    setLoading('submit');
    void (async () => {
      try {
        if (isSignup) {
          await signupWithNickname(name, password);
          nav.reset('privacy'); // 신규 → 온보딩(고양이 생성)으로
        } else {
          await loginWithNickname(name, password);
          nav.reset('home-night'); // 기존 → 바로 홈으로
        }
      } catch (e) {
        const status = e instanceof ApiError ? e.status : 0;
        if (isSignup && status === 409) {
          setHint({ ok: false, text: '이미 사용 중인 닉네임이에요' });
        } else if (!isSignup && status === 404) {
          setHint({ ok: false, text: '없는 닉네임이에요 · 회원가입해 주세요' });
        } else if (!isSignup && status === 401) {
          setHint({ ok: false, text: '비밀번호가 일치하지 않아요' });
        } else if (status === 400) {
          setHint({ ok: false, text: `닉네임 ${NICK_MAX}자 이내 · 비밀번호 ${PW_MIN}~${PW_MAX}자를 확인해 주세요` });
        } else {
          setHint({ ok: false, text: '실패 · 서버 연결을 확인해 주세요' });
        }
        setLoading(null);
      }
    })();
  };

  const onEnter = (e: KeyboardEvent) => {
    if (e.key === 'Enter') submit();
  };

  return (
    <div
      className="screen"
      style={{ background: '#fff9ee' }}
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
        <h1 className="h-display" style={{ fontSize: 40, marginTop: 14 }}>
          Tamaya
        </h1>
        <div className="handwriting" style={{ fontSize: 19, marginTop: 4, color: 'var(--ink-soft)' }}>
          {isSignup ? '반가워요! 닉네임을 만들어 주세요' : '다시 왔군요! 닉네임을 알려주세요'}
        </div>

        <div style={{ marginTop: 'auto', width: '100%' }}>
          <div className="tiny" style={labelStyle}>
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
                clearHint();
              }}
              onKeyDown={onEnter}
              style={inputStyle}
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

          <div className="tiny" style={{ ...labelStyle, marginTop: 12 }}>
            비밀번호
          </div>
          <div style={{ display: 'flex', gap: 8 }}>
            <input
              id="password"
              type="password"
              value={password}
              maxLength={PW_MAX}
              disabled={busy}
              placeholder={`비밀번호 (${PW_MIN}자 이상)`}
              aria-label="비밀번호"
              autoComplete={isSignup ? 'new-password' : 'current-password'}
              onChange={(e) => {
                setPassword(e.target.value);
                clearHint();
              }}
              onKeyDown={onEnter}
              style={inputStyle}
            />
          </div>

          {isSignup && (
            <>
              <div className="tiny" style={{ ...labelStyle, marginTop: 12 }}>
                비밀번호 확인
              </div>
              <div style={{ display: 'flex', gap: 8 }}>
                <input
                  id="password-confirm"
                  type="password"
                  value={passwordConfirm}
                  maxLength={PW_MAX}
                  disabled={busy}
                  placeholder="비밀번호를 한 번 더 입력해 주세요"
                  aria-label="비밀번호 확인"
                  autoComplete="new-password"
                  onChange={(e) => {
                    setPasswordConfirm(e.target.value);
                    clearHint();
                  }}
                  onKeyDown={onEnter}
                  style={inputStyle}
                />
              </div>
            </>
          )}

          {hint && (
            <div
              className="tiny"
              role={hint.ok ? 'status' : 'alert'}
              style={{
                marginTop: 8,
                textAlign: 'left',
                color: hint.ok ? 'var(--ok)' : 'var(--danger)',
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
