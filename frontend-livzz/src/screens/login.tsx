import { useState } from 'react';
import { CatSketch, StatusBar } from '../components/primitives';
import { useNav } from '../lib/router';

// 21 · Login — kakao + anonymous device_id (DEC-022.4 정합)

export const S21_Login = () => {
  const nav = useNav();
  const [loading, setLoading] = useState<'kakao' | 'anon' | null>(null);

  const enter = (kind: 'kakao' | 'anon') => {
    setLoading(kind);
    // simulate brief auth → onboarding entry
    setTimeout(() => {
      setLoading(null);
      nav.reset('welcome');
    }, 700);
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
