import { StatusBar, TabBar } from '../components/primitives';
import { useNav } from '../lib/router';
import { useStore } from '../lib/store';

// 22 · Settings — character name, notifications, data, logout

export const S22_Settings = () => {
  const nav = useNav();
  const { state, dispatch } = useStore();

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
    { label: '버전', value: 'v1.0 · Wireframes v3' },
  ];

  return (
    <div className="phone-inner">
      <StatusBar mode="day" time="11:42 AM" />
      <div className="phone-scroll" style={{ padding: '46px 18px 88px' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <span
            style={{ fontFamily: 'Caveat', fontSize: 22, cursor: 'pointer' }}
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
                <div style={{ fontFamily: 'Patrick Hand', fontWeight: 700 }}>{r.label}</div>
                <div className="tiny" style={{ marginTop: 2 }}>{r.value}</div>
              </div>
              {r.onClick && (
                <span style={{ fontFamily: 'Caveat', fontSize: 22 }}>›</span>
              )}
            </div>
          ))}
        </div>

        <div style={{ marginTop: 18 }}>
          <div className="h-label" style={{ marginBottom: 8 }}>현재 상태</div>
          <div className="hbox r-l" style={{ padding: 12 }}>
            <div className="tiny" style={{ marginBottom: 4 }}>
              포인트 · {state.points} ◉ / 스트릭 🔥 {state.streak}일 / Lv.{state.level}
            </div>
            <div className="tiny">아이템 {state.unlockedItems.length}개 · 입는중 {state.equippedItem ?? '없음'}</div>
          </div>
        </div>

        <button
          type="button"
          onClick={() => {
            if (confirm('모든 로컬 데이터를 초기화할까요?')) {
              localStorage.removeItem('tamaya-state-v2');
              location.reload();
            }
          }}
          className="btn block"
          style={{
            marginTop: 18,
            color: '#8a2c33',
            borderColor: '#8a2c33',
            background: '#fff',
            cursor: 'pointer',
            fontFamily: 'inherit',
          }}
        >
          데이터 초기화
        </button>

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
