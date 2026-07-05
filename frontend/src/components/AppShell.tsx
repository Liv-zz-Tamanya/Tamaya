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
import { S23_Coach } from '../screens/coach';
import { S24_Wellbeing } from '../screens/wellbeing';
import { S25_Byok } from '../screens/byok';
import { S26_HealthChat } from '../screens/health-chat';

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
  coach: () => <S23_Coach />,
  wellbeing: () => <S24_Wellbeing />,
  byok: () => <S25_Byok />,
  'health-chat': () => <S26_HealthChat />,
};

// Real-time-of-day determines whether the home tab routes to S06 (day) or
// S07 (night).
const isNightNow = () => {
  const h = new Date().getHours();
  return h >= 18 || h < 6;
};

export const AppShell = () => {
  const [stack, setStack] = useState<Route[]>(['splash']);
  const current = stack[stack.length - 1];
  const night = isNightNow();
  // The home screen is presentational day/night — resolve which one to render
  // from the current time-of-day so the home tab always shows the matching one.
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

  return (
    <StoreProvider>
      <NavContext.Provider value={api}>
        <div className="app-root">{SCREENS[displayRoute]()}</div>
      </NavContext.Provider>
    </StoreProvider>
  );
};
