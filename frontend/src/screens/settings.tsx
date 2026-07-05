import { useState } from 'react';
import { TabBar } from '../components/primitives';
import { useNav } from '../lib/router';
import { useStore } from '../lib/store';
import { purgeMyData } from '../lib/api';

// 22 · Settings — character name, notifications, data, logout

export const S22_Settings = () => {
  const nav = useNav();
  const { state, dispatch } = useStore();
  const [purging, setPurging] = useState(false);

  // 완전 삭제(liv-I1): 서버 device 데이터 purge(best-effort) + 로컬 store/세션 clear → 리로드.
  const purgeAll = async () => {
    if (!confirm('모든 데이터를 완전히 삭제할까요?\n· 서버: 일기·대화·정성신호·CLOVA설정·게임·인벤토리\n· 기기: 로컬 저장 전부\n되돌릴 수 없습니다.')) return;
    setPurging(true);
    let serverMsg = '서버 데이터 삭제 완료';
    try {
      const r = await purgeMyData();
      const n = Object.values(r.items_removed).reduce((a, b) => a + b, 0);
      serverMsg = `서버 데이터 삭제 완료 (${n}행)`;
    } catch {
      serverMsg = '서버 연결 실패 — 로컬만 삭제(서버는 기동 후 재시도)';
    }
    try {
      localStorage.removeItem('tamaya-state-v2');
      localStorage.removeItem('tamaya-auth-token');
      localStorage.removeItem('tamaya-chat-session');
      localStorage.removeItem('tamaya-healthchat-session');
    } catch {
      /* ignore */
    }
    alert(serverMsg + '\n기기 데이터 삭제 완료. 처음 화면으로 돌아갑니다.');
    location.reload();
  };

  const rows: {
    label: string;
    value: string;
    onClick?: () => void;
    danger?: boolean;
  }[] = [
    { label: '이음이 이름', value: state.character.name, onClick: () => nav.go('create-cat') },
    { label: '알림 — 회고 시간', value: '매일 22:00' },
    { label: '알림 — 주간 리포트', value: '월요일 09:00' },
    { label: '데이터 — 로컬 저장', value: `일기 ${state.diaries.length}건` },
    { label: '데이터 — 백업', value: '직접 내보내기' },
    { label: '🐱 밤 코칭 (건강냥)', value: 'BE 연동 · 코칭 대화', onClick: () => nav.go('coach') },
    { label: '📈 웰빙 인사이트', value: 'BE 연동 · 주간 스코어', onClick: () => nav.go('wellbeing') },
    { label: '✚ 건강 기록 Q&A', value: 'BE 연동 · RAG 챗', onClick: () => nav.go('health-chat') },
    { label: '🔑 CLOVA 키 (BYOK)', value: 'BE 연동 · 키 설정', onClick: () => nav.go('byok') },
    { label: '버전', value: 'v1.0 · healthcat-backend' },
  ];

  return (
    <div className="phone-inner">
      <div className="phone-scroll" style={{ padding: '46px 18px calc(88px + var(--safe-b, 0px))' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <span
            style={{ fontFamily: 'Pretendard', fontSize: 22, cursor: 'pointer' }}
            onClick={() => nav.back()}
          >
            ‹
          </span>
          <div className="h-title">설정</div>
        </div>

        <div style={{ marginTop: 14, display: 'flex', flexDirection: 'column', gap: 8 }}>
          {rows.map((r, i) => (
            <div
              key={i}
              onClick={r.onClick}
              className={'hbox ' + (i % 2 ? 'r-l' : 'r-r')}
              style={{
                padding: '12px 14px',
                display: 'flex',
                alignItems: 'center',
                gap: 10,
                cursor: r.onClick ? 'pointer' : 'default',
              }}
            >
              <div style={{ flex: 1 }}>
                <div style={{ fontFamily: 'Pretendard', fontWeight: 700 }}>{r.label}</div>
                <div className="tiny" style={{ marginTop: 2 }}>{r.value}</div>
              </div>
              {r.onClick && (
                <span style={{ fontFamily: 'Pretendard', fontSize: 22 }}>›</span>
              )}
            </div>
          ))}
        </div>

        <div style={{ marginTop: 18 }}>
          <div className="h-label" style={{ marginBottom: 8 }}>현재 상태</div>
          <div className="hbox r-l" style={{ padding: 12 }}>
            <div className="tiny" style={{ marginBottom: 4 }}>
              포인트 · {state.points} ◉ / 스트릭 {state.streak}일 / Lv.{state.level}
            </div>
            <div className="tiny">아이템 {state.unlockedItems.length}개 · 입는중 {state.equippedItem ?? '없음'}</div>
          </div>
        </div>

        <button
          type="button"
          onClick={() => void purgeAll()}
          disabled={purging}
          className="btn block"
          style={{
            marginTop: 18,
            color: '#8a2c33',
            borderColor: '#8a2c33',
            background: '#fff',
            cursor: purging ? 'wait' : 'pointer',
            fontFamily: 'inherit',
            opacity: purging ? 0.6 : 1,
          }}
        >
          {purging ? '완전 삭제 중…' : '데이터 완전 삭제 (서버 + 기기)'}
        </button>
        <div className="tiny" style={{ marginTop: 6, textAlign: 'center', color: 'var(--pencil)' }}>
          서버·기기의 내 데이터를 모두 지웁니다 · liv-zz Private-First 약속
        </div>

        <div style={{ marginTop: 10, textAlign: 'center' }}>
          <span
            className="tiny"
            style={{ cursor: 'pointer', color: '#7a5634' }}
            onClick={() => dispatch({ type: 'streak/inc' })}
          >
            (디버그) +1 스트릭
          </span>
        </div>
      </div>
      <TabBar active="home" />
    </div>
  );
};
