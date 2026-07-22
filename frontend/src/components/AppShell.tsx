import { ReactNode, useCallback, useEffect, useMemo, useState } from 'react';
import { getNightChatPreference, getNickname, getToken } from '../lib/api';
import {
  DEFAULT_NIGHT_CHAT_OPEN_TIME,
  activateManualWake,
  isManualWakeActive,
  isWithinNightWindow,
} from '../lib/nightChat';
import { NavApi, NavContext, Route } from '../lib/router';
import { StoreProvider } from '../lib/store';
import { S21_Login } from '../screens/login';
import { S22_Settings } from '../screens/settings';
import { S01_Splash, S02_Welcome, S03_Privacy, S04_CreateCat, S05_FirstMeet } from '../screens/onboarding';
import { S06_HomeDay, S07_HomeNight, S08_DailyCheck, S09_AIChat } from '../screens/home-day';
import { S10_RecapStart, S11_ChatDiary, S12_MoodFinalize, S13_Reward } from '../screens/evening';
import { S14_Calendar, S15_DiaryDetail, S16_Stats, S17_Insights } from '../screens/records';
import { S18_CatRoom, S19_Inventory, S20_Report } from '../screens/character';
import { S23_Coach } from '../screens/coach';
import { S24_Wellbeing } from '../screens/wellbeing';
import { S25_Byok } from '../screens/byok';
import { S26_HealthChat } from '../screens/health-chat';

const SCREENS: Record<Route, () => ReactNode> = {
  splash: () => <S01_Splash />, welcome: () => <S02_Welcome />, privacy: () => <S03_Privacy />,
  'create-cat': () => <S04_CreateCat />, 'first-meet': () => <S05_FirstMeet />,
  'home-day': () => <S06_HomeDay />, 'home-night': () => <S07_HomeNight />,
  'daily-check': () => <S08_DailyCheck />, 'ai-chat': () => <S09_AIChat />,
  'recap-start': () => <S10_RecapStart />, 'chat-diary': () => <S11_ChatDiary />,
  'mood-finalize': () => <S12_MoodFinalize />, reward: () => <S13_Reward />,
  calendar: () => <S14_Calendar />, 'diary-detail': () => <S15_DiaryDetail />,
  stats: () => <S16_Stats />, insights: () => <S17_Insights />, 'cat-room': () => <S18_CatRoom />,
  inventory: () => <S19_Inventory />, report: () => <S20_Report />, login: () => <S21_Login />,
  settings: () => <S22_Settings />, coach: () => <S23_Coach />, wellbeing: () => <S24_Wellbeing />,
  byok: () => <S25_Byok />, 'health-chat': () => <S26_HealthChat />,
};

export const AppShell = () => <StoreProvider><AppShellInner /></StoreProvider>;

const AppShellInner = () => {
  const initialRoute = (): Route => {
    if (import.meta.env.DEV) {
      const m = window.location.hash.match(/^#s=([\w-]+)$/);
      if (m && m[1] in SCREENS) return m[1] as Route;
    }
    return 'splash';
  };
  const [stack, setStack] = useState<Route[]>([initialRoute()]);
  const [now, setNow] = useState(() => new Date());
  const [openTime, setOpenTime] = useState(DEFAULT_NIGHT_CHAT_OPEN_TIME);
  const [timezone, setTimezone] = useState('Asia/Seoul');
  const [preferenceLoading, setPreferenceLoading] = useState(() => getToken() !== null);
  const [manualWake, setManualWake] = useState(() => isManualWakeActive(getNickname()));
  const current = stack[stack.length - 1];

  const refreshNow = useCallback(() => {
    const next = new Date();
    setNow(next);
    setManualWake(isManualWakeActive(getNickname(), next));
  }, []);

  useEffect(() => {
    const timer = window.setInterval(refreshNow, 30_000);
    const onVisible = () => { if (document.visibilityState === 'visible') refreshNow(); };
    window.addEventListener('focus', refreshNow);
    document.addEventListener('visibilitychange', onVisible);
    return () => {
      window.clearInterval(timer);
      window.removeEventListener('focus', refreshNow);
      document.removeEventListener('visibilitychange', onVisible);
    };
  }, [refreshNow]);

  useEffect(() => {
    let cancelled = false;
    const load = async () => {
      if (!getToken()) {
        if (!cancelled) setPreferenceLoading(false);
        return;
      }
      setPreferenceLoading(true);
      try {
        const preference = await getNightChatPreference();
        if (!cancelled) { setOpenTime(preference.open_time); setTimezone(preference.timezone); }
      } catch {
        if (!cancelled) { setOpenTime(DEFAULT_NIGHT_CHAT_OPEN_TIME); setTimezone('Asia/Seoul'); }
      } finally {
        if (!cancelled) setPreferenceLoading(false);
      }
    };
    void load();
    window.addEventListener('tamaya-auth-changed', load);
    return () => { cancelled = true; window.removeEventListener('tamaya-auth-changed', load); };
  }, []);

  const night = isWithinNightWindow(now, openTime) || manualWake;
  const go = useCallback((r: Route) => setStack((s) => [...s, r]), []);
  const back = useCallback(() => setStack((s) => (s.length > 1 ? s.slice(0, -1) : s)), []);
  const reset = useCallback((r: Route) => setStack([r]), []);
  const setNightOpenTime = useCallback((next: string, nextTimezone: string) => {
    setOpenTime(next); setTimezone(nextTimezone); refreshNow();
  }, [refreshNow]);
  const wakeNightChat = useCallback(() => {
    const nickname = getNickname();
    if (nickname) activateManualWake(nickname);
    setManualWake(true);
    setStack((s) => [...s, 'home-night']);
  }, []);

  // Only the home route is redirected when the window closes. In-progress recap
  // routes remain available so a 06:00 transition cannot discard typed content.
  const displayRoute: Route =
    preferenceLoading && (current === 'home-day' || current === 'home-night') ? current :
    (current === 'home-day' || current === 'home-night') ? (night ? 'home-night' : 'home-day') : current;
  const api = useMemo<NavApi>(
    () => ({ go, back, reset, current, night, now, nightOpenTime: openTime, nightTimezone: timezone, setNightOpenTime, wakeNightChat }),
    [go, back, reset, current, night, now, openTime, timezone, setNightOpenTime, wakeNightChat],
  );

  return <NavContext.Provider value={api}><div className="app-root">{SCREENS[displayRoute]()}</div></NavContext.Provider>;
};
