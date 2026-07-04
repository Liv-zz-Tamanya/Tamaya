import { useState } from 'react';
import { CatSketch, StatusBar } from '../components/primitives';
import { useNav } from '../lib/router';
import { checkNickname, ensureDeviceToken, loginWithNickname } from '../lib/api';

// 21 · Login — 닉네임 회원가입/로그인 통합 (데모: 비밀번호 없음)
// 닉네임 입력 → [중복확인]으로 신규/기존 안내 → [시작하기]로 가입 or 로그인.
// 로그인 시 데이터 네임스페이스(device_id)가 닉네임 계정으로 고정 → 닉네임별 자기 데이터.
// '익명으로 둘러보기'는 기존 device 익명 진입 폴백으로 유지.

const NICK_MAX = 16;

export const S21_Login = () => {
  const nav = useNav();
  const [nickname, setNickname] = useState('');
  const [loading, setLoading] = useState<'check' | 'start' | 'anon' | null>(null);
  const [hint, setHint] = useState<{ ok: boolean; text: string } | null>(null);

  const busy = loading !== null;

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
            ? { ok: true, text: '사용 가능한 새 닉네임이에요 · 시작하면 가입돼요' }
            : { ok: true, text: '이미 있는 닉네임이에요 · 시작하면 이어서 로그인돼요' },
        );
      } catch {
        setHint({ ok: false, text: '확인 실패 · 서버 연결을 확인해 주세요' });
      } finally {
        setLoading(null);
      }
    })();
  };

  const start = () => {
    const name = nickname.trim();
    if (!name) {
      setHint({ ok: false, text: '닉네임을 입력해 주세요' });
      return;
    }
    setLoading('start');
    void (async () => {
      try {
        await loginWithNickname(name);
        nav.reset('welcome');
      } catch {
        setHint({ ok: false, text: '시작 실패 · 서버 연결을 확인해 주세요' });
        setLoading(null);
      }
    })();
  };

  const enterAnon = () => {
    setLoading('anon');
    void (async () => {
      try {
        await ensureDeviceToken();
      } catch {
        // BE 미기동/오프라인 — 진입은 막지 않음(토큰은 첫 API 호출 때 재시도)
      } finally {
        setLoading(null);
        nav.reset('welcome');
      }
    })();
  };

  return (
    <div
      className="phone-inner"
      style={{
        background: 'linear-gradient(180deg, #f5e6cf 0%, #ead0a6 70%, #d8a777 100%)',
      }}
    >
      <StatusBar mode="day" time="9:00 AM" />
      <div
        style={{
          padding: '60px 24px 24px',
          height: '100%',
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          textAlign: 'center',
        }}
      >
        <div
          style={{
            background: '#f5e6cf',
            borderRadius: '50%',
            padding: 16,
            border: '2px solid #3a2414',
            marginTop: 24,
          }}
        >
          <CatSketch size={96} mood="happy" />
        </div>
        <div className="h-display" style={{ fontSize: 40, marginTop: 14 }}>
          Tamaya
        </div>
        <div className="handwriting" style={{ fontSize: 19, marginTop: 4, color: '#5a3a22' }}>
          매일 작은 루틴을 함께 키우는 AI 친구
        </div>

        <div style={{ marginTop: 'auto', width: '100%' }}>
          <label
            className="tiny"
            htmlFor="nickname"
            style={{ display: 'block', textAlign: 'left', color: '#5a3a22', marginBottom: 6 }}
          >
            닉네임으로 시작하기
          </label>
          <div style={{ display: 'flex', gap: 8 }}>
            <input
              id="nickname"
              type="text"
              value={nickname}
              maxLength={NICK_MAX}
              disabled={busy}
              placeholder={`닉네임 (최대 ${NICK_MAX}자)`}
              onChange={(e) => {
                setNickname(e.target.value);
                setHint(null);
              }}
              onKeyDown={(e) => {
                if (e.key === 'Enter') start();
              }}
              style={{
                flex: 1,
                minWidth: 0,
                padding: '12px 14px',
                borderRadius: 12,
                border: '1.5px solid #3a2414',
                background: '#fff9ef',
                color: '#3a2414',
                fontFamily: 'inherit',
                fontSize: 16,
              }}
            />
            <button
              type="button"
              disabled={busy}
              onClick={doCheck}
              className="btn"
              style={{
                flexShrink: 0,
                background: '#fff9ef',
                color: '#3a2414',
                border: '1.5px solid #3a2414',
                cursor: busy ? 'wait' : 'pointer',
                fontFamily: 'inherit',
                padding: '0 14px',
              }}
            >
              {loading === 'check' ? '…' : '중복확인'}
            </button>
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
            onClick={start}
            className="btn primary block"
            style={{
              marginTop: 14,
              cursor: busy ? 'wait' : 'pointer',
              fontFamily: 'inherit',
            }}
          >
            {loading === 'start' ? '잠시만요…' : '시작하기'}
          </button>

          <button
            type="button"
            disabled={busy}
            onClick={enterAnon}
            style={{
              marginTop: 12,
              background: 'none',
              border: 'none',
              color: '#5a3a22',
              textDecoration: 'underline',
              cursor: busy ? 'wait' : 'pointer',
              fontFamily: 'inherit',
              fontSize: 13,
            }}
          >
            {loading === 'anon' ? '잠시만요…' : '익명으로 둘러보기'}
          </button>
          <div className="tiny" style={{ marginTop: 8, color: '#5a3a22' }}>
            * 데모용 · 닉네임만으로 가입/로그인 (비밀번호 없음)
          </div>
        </div>
      </div>
    </div>
  );
};
