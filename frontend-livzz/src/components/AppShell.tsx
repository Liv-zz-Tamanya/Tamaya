import { ReactNode, useCallback, useMemo, useState } from 'react';
import { NavApi, NavContext, Route } from '../lib/router';
import { StoreProvider } from '../lib/store';
import { S21_Login } from '../screens/login';
import { S22_Settings } from '../screens/settings';
import {
  S01_Splash,
  S02_Welcome,
  S03_Privacy,
  S04_CreateCat,
  S05_FirstMeet,
} from '../screens/onboarding';
import {
  S06_HomeDay,
  S07_HomeNight,
  S08_DailyCheck,
  S09_AIChat,
} from '../screens/home-day';
import {
  S10_RecapStart,
  S11_ChatDiary,
  S12_MoodFinalize,
  S13_Reward,
} from '../screens/evening';
import {
  S14_Calendar,
  S15_DiaryDetail,
  S16_Stats,
  S17_Insights,
} from '../screens/records';
import { S18_CatRoom, S19_Inventory, S20_Report } from '../screens/character';

const SCREENS: Record<Route, () => ReactNode> = {
  splash: () => <S01_Splash />,
  welcome: () => <S02_Welcome />,
  privacy: () => <S03_Privacy />,
  'create-cat': () => <S04_CreateCat />,
  'first-meet': () => <S05_FirstMeet />,
  'home-day': () => <S06_HomeDay />,
  'home-night': () => <S07_HomeNight />,
  'daily-check': () => <S08_DailyCheck />,
  'ai-chat': () => <S09_AIChat />,
  'recap-start': () => <S10_RecapStart />,
  'chat-diary': () => <S11_ChatDiary />,
  'mood-finalize': () => <S12_MoodFinalize />,
  reward: () => <S13_Reward />,
  calendar: () => <S14_Calendar />,
  'diary-detail': () => <S15_DiaryDetail />,
  stats: () => <S16_Stats />,
  insights: () => <S17_Insights />,
  'cat-room': () => <S18_CatRoom />,
  inventory: () => <S19_Inventory />,
  report: () => <S20_Report />,
  login: () => <S21_Login />,
  settings: () => <S22_Settings />,
};

const ROUTE_LABEL: Record<Route, string> = {
  splash: '01 Splash',
  welcome: '02 Welcome',
  privacy: '03 Privacy',
  'create-cat': '04 캐릭터 생성',
  'first-meet': '05 첫 만남',
  'home-day': '06 홈 (낮)',
  'home-night': '07 홈 (밤)',
  'daily-check': '08 데일리 체크',
  'ai-chat': '09 AI 코칭',
  'recap-start': '10 회고 시작',
  'chat-diary': '11 ChatDiary 5턴',
  'mood-finalize': '12 감정 분석·일기',
  reward: '13 보상 모달',
  calendar: '14 달력',
  'diary-detail': '15 일기 디테일',
  stats: '16 통계',
  insights: '17 인사이트',
  'cat-room': '18 이음이 방',
  inventory: '19 인벤토리',
  report: '20 주간 리포트',
  login: '21 로그인',
  settings: '22 설정',
};

// Real-time-of-day determines whether the home tab routes to S06 (day) or
// S07 (night). Manual override via the top toolbar.
type Mode = 'auto' | 'day' | 'night';
const isNightNow = () => {
  const h = new Date().getHours();
  return h >= 18 || h < 6;
};

export const AppShell = ({ onExitToDesign }: { onExitToDesign: () => void }) => {
  const [stack, setStack] = useState<Route[]>(['splash']);
  const [mode, setMode] = useState<Mode>('auto');
  const current = stack[stack.length - 1];
  const night = mode === 'auto' ? isNightNow() : mode === 'night';
  // The home screen is presentational day/night — resolve which one to render
  // from the current time-of-day so the toolbar toggle (and the home tab) always
  // show the matching screen, however the user arrived.
  const displayRoute: Route =
    current === 'home-day' || current === 'home-night'
      ? night
        ? 'home-night'
        : 'home-day'
      : current;

  const go = useCallback((r: Route) => setStack((s) => [...s, r]), []);
  const back = useCallback(
    () => setStack((s) => (s.length > 1 ? s.slice(0, -1) : s)),
    [],
  );
  const reset = useCallback((r: Route) => setStack([r]), []);

  const api = useMemo<NavApi>(
    () => ({ go, back, reset, current, night }),
    [go, back, reset, current, night],
  );

  // Public helper for the header dropdown — jump to any screen, fresh history.
  const jump = (r: Route) => reset(r);

  // Hook the time-of-day decision into the home tab — passed indirectly via
  // a default behavior, but the TabBar's onHome prop is already wired per
  // screen. We only need to ensure a sane default landing when /home picked.

  // ── chrome / layout ────────────────────────────────────────────────
  return (
    <StoreProvider>
      <NavContext.Provider value={api}>
        <div
          className="app-shell"
          style={{
            minHeight: '100vh',
            background: '#f5f1e8',
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
            fontFamily: '-apple-system, BlinkMacSystemFont, system-ui, sans-serif',
            paddingTop: 32,
            paddingBottom: 48,
          }}
        >
          <Toolbar
            current={displayRoute}
            stack={stack}
            mode={mode}
            night={night}
            onJump={jump}
            onMode={setMode}
            onBack={back}
            onExitToDesign={onExitToDesign}
          />

          <div className="phone-frame" style={{ marginTop: 16, position: 'relative' }}>
            <div className="phone sketch">{SCREENS[displayRoute]()}</div>
          </div>

          <div className="app-hint">
            <Hint />
          </div>
        </div>
      </NavContext.Provider>
    </StoreProvider>
  );
};

const Toolbar = ({
  current,
  stack,
  mode,
  night,
  onJump,
  onMode,
  onBack,
  onExitToDesign,
}: {
  current: Route;
  stack: Route[];
  mode: Mode;
  night: boolean;
  onJump: (r: Route) => void;
  onMode: (m: Mode) => void;
  onBack: () => void;
  onExitToDesign: () => void;
}) => {
  const [open, setOpen] = useState(false);
  return (
    <div
      className="app-toolbar"
      style={{
        width: 'min(640px, 96vw)',
        background: '#fff',
        border: '1.5px solid #3a2414',
        borderRadius: 14,
        padding: '10px 14px',
        display: 'flex',
        alignItems: 'center',
        gap: 10,
        fontSize: 13,
        boxShadow: '0 1px 4px rgba(0,0,0,0.06)',
        flexWrap: 'wrap',
        position: 'relative',
        zIndex: 20,
      }}
    >
      <span style={{ fontWeight: 700, color: '#3a2414' }}>Tamaya · 앱 미리보기</span>
      <span style={{ opacity: 0.4 }}>·</span>
      <button
        type="button"
        onClick={onBack}
        disabled={stack.length <= 1}
        style={{
          padding: '4px 10px',
          background: stack.length > 1 ? '#f5e6cf' : '#fafafa',
          color: stack.length > 1 ? '#3a2414' : '#bbb',
          border: '1px solid ' + (stack.length > 1 ? '#3a2414' : '#ddd'),
          borderRadius: 8,
          cursor: stack.length > 1 ? 'pointer' : 'not-allowed',
          fontFamily: 'inherit',
          fontSize: 12,
        }}
      >
        ‹ 뒤로
      </button>

      <div style={{ position: 'relative' }}>
        <button
          type="button"
          onClick={() => setOpen((o) => !o)}
          style={{
            padding: '4px 10px',
            background: '#fff',
            border: '1px solid #3a2414',
            borderRadius: 8,
            cursor: 'pointer',
            fontFamily: 'inherit',
            fontSize: 12,
            color: '#3a2414',
          }}
        >
          {ROUTE_LABEL[current]} ▾
        </button>
        {open && (
          <div
            style={{
              position: 'absolute',
              top: '100%',
              left: 0,
              marginTop: 4,
              background: '#fff',
              border: '1.5px solid #3a2414',
              borderRadius: 8,
              padding: 4,
              minWidth: 200,
              maxHeight: 360,
              overflowY: 'auto',
              boxShadow: '0 6px 24px rgba(0,0,0,0.12)',
              zIndex: 30,
            }}
          >
            {(Object.entries(ROUTE_LABEL) as [Route, string][]).map(([r, label]) => (
              <button
                key={r}
                type="button"
                onClick={() => {
                  onJump(r);
                  setOpen(false);
                }}
                style={{
                  display: 'block',
                  width: '100%',
                  textAlign: 'left',
                  padding: '6px 10px',
                  background: r === current ? '#f5e6cf' : 'transparent',
                  border: 'none',
                  borderRadius: 4,
                  cursor: 'pointer',
                  fontFamily: 'inherit',
                  fontSize: 13,
                  color: '#3a2414',
                }}
              >
                {label}
              </button>
            ))}
          </div>
        )}
      </div>

      <span style={{ opacity: 0.4 }}>·</span>
      <span style={{ fontSize: 11, color: '#7a5634' }}>시간대</span>
      {(['auto', 'day', 'night'] as Mode[]).map((m) => (
        <button
          key={m}
          type="button"
          onClick={() => onMode(m)}
          style={{
            padding: '4px 8px',
            background: mode === m ? '#3a2414' : '#fff',
            color: mode === m ? '#f5e6cf' : '#3a2414',
            border: '1px solid #3a2414',
            borderRadius: 6,
            cursor: 'pointer',
            fontFamily: 'inherit',
            fontSize: 11,
          }}
        >
          {m}
          {m === 'auto' ? ` (${night ? '밤' : '낮'})` : ''}
        </button>
      ))}

      <span style={{ flex: 1 }} />
      <button
        type="button"
        onClick={onExitToDesign}
        style={{
          padding: '4px 10px',
          background: 'transparent',
          border: '1px dashed #7a5634',
          borderRadius: 8,
          cursor: 'pointer',
          fontFamily: 'inherit',
          fontSize: 12,
          color: '#7a5634',
        }}
      >
        ⤴ 와이어프레임 캔버스
      </button>
    </div>
  );
};

const Bezel = () => (
  // Decorative phone bezel — not interactive, sits behind .phone.
  null
);

const Hint = () => (
  <div
    style={{
      marginTop: 24,
      maxWidth: 420,
      textAlign: 'center',
      fontSize: 12,
      color: '#7a5634',
      lineHeight: 1.6,
    }}
  >
    상단의 화면 선택 메뉴로 바로 점프 · 폰 안의 버튼/카드 클릭으로 흐름 진행 · 시간대 토글로
    홈 낮↔밤 전환
  </div>
);
