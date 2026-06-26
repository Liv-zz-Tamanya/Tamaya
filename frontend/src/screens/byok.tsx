import { useEffect, useState } from 'react';
import { StatusBar, TabBar } from '../components/primitives';
import { useNav } from '../lib/router';
import { getClovaSetting, testClovaKey, saveClovaKey, type ClovaSetting } from '../lib/api';

// S25 · BYOK CLOVA 키 설정 (건강냥 Medlife) — 사용자 키를 요청별로 사용.
// 보안 불변식: 원문 키는 요청 본문으로만 가고, 응답·저장소엔 마스킹(••••last4)만 남는다.
// 건강냥이 BE: /api/v1/settings/clova {GET, /test, PUT}

export const S25_Byok = ({ sample = false }: { sample?: boolean } = {}) => {
  const nav = useNav();
  // 와이어프레임 캔버스(#design)에선 "키 등록됨" 상태를 샘플로 보여준다(백엔드 불필요).
  const [setting, setSetting] = useState<ClovaSetting | null>(
    sample ? { has_key: true, masked: '••••3f9c' } : null,
  );
  const [key, setKey] = useState('');
  const [busy, setBusy] = useState<false | 'test' | 'save' | 'load'>(sample ? false : 'load');
  const [msg, setMsg] = useState<{ kind: 'ok' | 'err'; text: string } | null>(null);

  useEffect(() => {
    if (sample) return;
    void (async () => {
      try {
        setSetting(await getClovaSetting());
      } catch {
        setMsg({ kind: 'err', text: '저장된 설정을 불러오지 못했어요 (서버 연결 확인).' });
      } finally {
        setBusy(false);
      }
    })();
  }, [sample]);

  const onTest = () => {
    if (!key.trim()) return;
    setBusy('test');
    setMsg(null);
    void (async () => {
      try {
        const r = await testClovaKey(key.trim());
        setMsg(
          r.ok
            ? { kind: 'ok', text: `연결 성공 · ${r.masked}` }
            : { kind: 'err', text: `연결 실패 · ${r.masked} (키를 확인해 주세요)` },
        );
      } catch {
        setMsg({ kind: 'err', text: '테스트 호출 실패 (서버 연결 확인).' });
      } finally {
        setBusy(false);
      }
    })();
  };

  const onSave = () => {
    if (!key.trim()) return;
    setBusy('save');
    setMsg(null);
    void (async () => {
      try {
        const s = await saveClovaKey(key.trim());
        setSetting(s);
        setKey('');
        setMsg({ kind: 'ok', text: `저장됨 · ${s.masked} (원문 키는 서버에 저장되지 않음)` });
      } catch {
        setMsg({ kind: 'err', text: '저장 실패 (서버 연결 확인).' });
      } finally {
        setBusy(false);
      }
    })();
  };

  return (
    <div className="phone-inner">
      <StatusBar mode="day" time="10:05 AM" />
      <div className="phone-scroll" style={{ padding: '46px 18px 88px' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <span style={{ fontFamily: 'Pretendard', fontSize: 22, cursor: 'pointer' }} onClick={() => nav.back()}>‹</span>
          <div className="h-title">CLOVA 키 (BYOK)</div>
        </div>
        <div className="tiny" style={{ marginTop: 2, marginBottom: 14 }}>
          내 CLOVA 키를 요청별로 사용 · 없으면 mock으로 동작
        </div>

        <div className="hbox r-l" style={{ padding: 14 }}>
          <div className="tiny">현재 상태</div>
          <div className="body" style={{ marginTop: 4, fontWeight: 700 }}>
            {busy === 'load'
              ? '확인 중…'
              : setting?.has_key
                ? `키 등록됨 · ${setting.masked}`
                : '등록된 키 없음 (mock 모드)'}
          </div>
        </div>

        <div className="h-label" style={{ marginTop: 18, marginBottom: 6 }}>CLOVA Studio API 키</div>
        <input
          value={key}
          onChange={(e) => setKey(e.target.value)}
          placeholder="nv-..."
          type="password"
          style={{
            width: '100%',
            padding: '12px 14px',
            border: '1.5px solid #3a2414',
            borderRadius: 10,
            fontFamily: 'inherit',
            fontSize: 14,
            background: '#fff',
          }}
        />

        <div style={{ display: 'flex', gap: 8, marginTop: 12 }}>
          <button
            type="button"
            onClick={onTest}
            disabled={!key.trim() || busy !== false}
            className="btn"
            style={{ flex: 1, cursor: key.trim() && busy === false ? 'pointer' : 'not-allowed', fontFamily: 'inherit', opacity: busy === 'test' ? 0.6 : 1 }}
          >
            {busy === 'test' ? '테스트 중…' : '연결 테스트'}
          </button>
          <button
            type="button"
            onClick={onSave}
            disabled={!key.trim() || busy !== false}
            className="btn primary"
            style={{ flex: 1, cursor: key.trim() && busy === false ? 'pointer' : 'not-allowed', fontFamily: 'inherit', opacity: busy === 'save' ? 0.6 : 1 }}
          >
            {busy === 'save' ? '저장 중…' : '저장'}
          </button>
        </div>

        {msg && (
          <div
            className="hbox"
            style={{ marginTop: 14, padding: 12, color: msg.kind === 'ok' ? 'var(--accent)' : '#8a2c33' }}
          >
            <div className="body">{msg.kind === 'ok' ? '✓ ' : '⚠ '}{msg.text}</div>
          </div>
        )}

        <div className="tiny" style={{ marginTop: 16, color: '#7a5634' }}>
          ※ 키는 마스킹 프리뷰(••••last4)만 device 기준 저장됩니다. 원문 키는 서버에 저장되지 않아요.
        </div>
      </div>
      <TabBar active="home" />
    </div>
  );
};
