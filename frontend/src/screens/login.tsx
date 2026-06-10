import { useState } from 'react';
import { CatSketch, StatusBar } from '../components/primitives';
import { useNav } from '../lib/router';
import { ensureDeviceToken } from '../lib/api';

// 21 · Login — kakao + anonymous device_id (DEC-022.4 정합)
// 건강냥이 BE 연동: 익명/카카오 모두 POST /auth/device 로 device 토큰 확보.
// (실 카카오 OAuth code 플로우는 Phase 2. PoC는 device 신원으로 진입.)
// BE 미기동/오프라인이어도 온보딩은 진행(graceful) — 토큰은 다음 호출 때 lazy 확보.

export const S21_Login = () => {
  const nav = useNav();
  const [loading, setLoading] = useState<'kakao' | 'anon' | null>(null);

  const enter = (kind: 'kakao' | 'anon') => {
    setLoading(kind);
    void (async () => {
      try {
        await ensureDeviceToken(); // 실제 /auth/device 토큰 확보 (liv-I1: device_id 익명)
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
            marginTop: 40,
          }}
        >
          <CatSketch size={110} mood="happy" />
        </div>
        <div className="h-display" style={{ fontSize: 42, marginTop: 16 }}>
          Tamaya
        </div>
        <div className="handwriting" style={{ fontSize: 20, marginTop: 4, color: '#5a3a22' }}>
          매일 작은 루틴을 함께 키우는 AI 친구
        </div>

        <div style={{ marginTop: 'auto', width: '100%' }}>
          <button
            type="button"
            disabled={loading !== null}
            onClick={() => enter('kakao')}
            className="btn block"
            style={{
              background: '#FEE500',
              color: '#3a2414',
              border: '1.5px solid #3a2414',
              cursor: loading ? 'wait' : 'pointer',
              fontFamily: 'inherit',
              marginBottom: 10,
            }}
          >
            {loading === 'kakao' ? '잠시만요…' : '💬 카카오로 시작'}
          </button>
          <button
            type="button"
            disabled={loading !== null}
            onClick={() => enter('anon')}
            className="btn primary block"
            style={{
              cursor: loading ? 'wait' : 'pointer',
              fontFamily: 'inherit',
            }}
          >
            {loading === 'anon' ? '잠시만요…' : '익명으로 둘러보기'}
          </button>
          <div className="tiny" style={{ marginTop: 10, color: '#5a3a22' }}>
            * 익명도 모든 기능 사용 가능 · 데이터는 이 기기에만
          </div>
        </div>
      </div>
    </div>
  );
};
