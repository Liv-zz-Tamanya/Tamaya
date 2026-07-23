import { useState } from 'react';
import { BackButton, TabBar } from '../components/primitives';
import { useNav } from '../lib/router';
import { useStore } from '../lib/store';
import { purgeMyData, updateNightChatPreference } from '../lib/api';

// 22 · Settings — character name, notifications, data, logout

export const S22_Settings = () => {
  const nav = useNav();
  const { state, dispatch } = useStore();
  const [purging, setPurging] = useState(false);
  const [openTime, setOpenTime] = useState(nav.nightOpenTime);
  const [saving, setSaving] = useState(false);
  const [saveStatus, setSaveStatus] = useState<string | null>(null);

  const saveNightChatTime = async () => {
    if (!/^([01]\d|2[0-3]):[0-5]\d$/.test(openTime) || openTime < '18:00') {
      setSaveStatus('밤 채팅 시작 시간은 18:00~23:59 사이여야 해요.');
      return;
    }
    setSaving(true);
    setSaveStatus(null);
    try {
      const saved = await updateNightChatPreference({
        open_time: openTime,
        timezone: nav.nightTimezone,
      });
      setOpenTime(saved.open_time);
      nav.setNightOpenTime(saved.open_time, saved.timezone);
      setSaveStatus('저장했어요.');
    } catch {
      setOpenTime(nav.nightOpenTime);
      setSaveStatus('저장하지 못했어요. 기존 설정을 유지합니다.');
    } finally {
      setSaving(false);
    }
  };

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
    { label: '알림 — 주간 리포트', value: '월요일 09:00' },
    { label: '데이터 — 로컬 저장', value: `일기 ${state.diaries.length}건` },
    { label: '🐱 밤 코칭 (건강냥)', value: 'BE 연동 · 코칭 대화', onClick: () => nav.go('coach') },
    { label: '📈 웰빙 인사이트', value: 'BE 연동 · 주간 스코어', onClick: () => nav.go('wellbeing') },
    { label: '✚ 건강 기록 Q&A', value: 'BE 연동 · RAG 챗', onClick: () => nav.go('health-chat') },
    { label: '🔑 CLOVA 키 (BYOK)', value: 'BE 연동 · 키 설정', onClick: () => nav.go('byok') },
    { label: '버전', value: 'v1.0 · healthcat-backend' },
  ];

  return (
    <div className="screen">
      <div className="screen-scroll" style={{ padding: 'calc(46px + var(--safe-t)) 18px calc(88px + var(--safe-b, 0px))' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <BackButton onClick={() => nav.back()} tone="var(--ink)" />
          <h1 className="h-title">설정</h1>
        </div>

        <div style={{ marginTop: 16, display: 'flex', flexDirection: 'column', gap: 10 }}>
          <div className="hbox" style={{ padding: '12px 14px' }}>
            <div style={{ fontWeight: 700, fontSize: 14 }}>밤 채팅 시작 시간</div>
            <div className="tiny" style={{ marginTop: 3, color: 'var(--pencil)' }}>매일 설정한 시간부터 다음 날 06:00까지</div>
            <div style={{ display: 'flex', gap: 8, marginTop: 8, alignItems: 'center' }}>
              <input
                aria-label="밤 채팅 시작 시간"
                type="time"
                min="18:00"
                max="23:59"
                value={openTime}
                onChange={(event) => setOpenTime(event.target.value)}
                disabled={saving}
                style={{ fontSize: 16 }}
              />
              <button type="button" className="btn" onClick={() => void saveNightChatTime()} disabled={saving} style={{ cursor: saving ? 'wait' : 'pointer', fontFamily: 'inherit' }}>
                {saving ? '저장 중…' : '저장'}
              </button>
            </div>
            {saveStatus && <div className="tiny" role="status" style={{ marginTop: 6, color: 'var(--pencil)' }}>{saveStatus}</div>}
          </div>
          {rows.map((r, i) => {
            const rowContent = (
              <>
                <div style={{ flex: 1 }}>
                  <div style={{ fontWeight: 700, fontSize: 14 }}>{r.label}</div>
                  <div className="tiny" style={{ marginTop: 3, color: 'var(--pencil)' }}>{r.value}</div>
                </div>
                {r.onClick && (
                  <span style={{ fontSize: 22, color: 'var(--ink)' }} aria-hidden="true">›</span>
                )}
              </>
            );
            const rowStyle = {
              padding: '12px 14px',
              display: 'flex',
              alignItems: 'center',
              gap: 10,
              cursor: r.onClick ? 'pointer' : 'default',
            };
            return r.onClick ? (
              <button
                key={i}
                type="button"
                onClick={r.onClick}
                className="hbox as-button"
                aria-label={`${r.label} — ${r.value}`}
                style={{ ...rowStyle, width: '100%', textAlign: 'left' as const }}
              >
                {rowContent}
              </button>
            ) : (
              <div key={i} className="hbox" style={rowStyle}>
                {rowContent}
              </div>
            );
          })}
        </div>

        <div style={{ marginTop: 20 }}>
          <h2 className="h-label" style={{ marginBottom: 8 }}>현재 상태</h2>
          <div className="hbox" style={{ padding: '12px 14px' }}>
            <div className="tiny" style={{ marginBottom: 5, color: 'var(--ink)' }}>
              포인트 · {state.points} ◉ / 스트릭 {state.streak}일 / Lv.{state.level}
            </div>
            <div className="tiny" style={{ color: 'var(--pencil)' }}>아이템 {state.unlockedItems.length}개 · 입는중 {state.equippedItem ?? '없음'}</div>
          </div>
        </div>

        <button
          type="button"
          onClick={() => void purgeAll()}
          disabled={purging}
          className="btn block"
          style={{
            marginTop: 20,
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

        {import.meta.env.DEV && (
          <div style={{ marginTop: 10, textAlign: 'center' }}>
            <button
              type="button"
              className="tiny as-button"
              style={{ cursor: 'pointer', color: 'var(--pencil)' }}
              onClick={() => dispatch({ type: 'streak/inc' })}
            >
              (디버그) +1 스트릭
            </button>
          </div>
        )}
      </div>
      <TabBar active="home" />
    </div>
  );
};
