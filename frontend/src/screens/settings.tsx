import { useState } from 'react';
import { BackButton, TabBar } from '../components/primitives';
import { useNav } from '../lib/router';
import { useStore } from '../lib/store';
import { updateNightChatPreference } from '../lib/api';

// 22 · Settings — character name, notifications, data, logout

export const S22_Settings = () => {
  const nav = useNav();
  const { state } = useStore();
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

  // 설정 화면에는 사용자에게 제공하는 항목만 둔다.
  const rows: {
    label: string;
    value: string;
    onClick?: () => void;
    danger?: boolean;
  }[] = [
    { label: '이음이 이름', value: state.character.name, onClick: () => nav.go('create-cat') },
    { label: '버전', value: 'v1.0 · tamaya.online' },
  ];

  const rowNodes = rows.map((r, i) => {
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
  });

  return (
    <div className="screen">
      <div className="screen-scroll" style={{ padding: 'calc(46px + var(--safe-t)) 18px calc(88px + var(--safe-b, 0px))' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <BackButton onClick={() => nav.back()} tone="var(--ink)" />
          <h1 className="h-title">설정</h1>
        </div>

        <div style={{ marginTop: 16, display: 'flex', flexDirection: 'column', gap: 10 }}>
          {rowNodes[0]}
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
          {rowNodes[1]}
        </div>
      </div>
      <TabBar active="home" />
    </div>
  );
};
