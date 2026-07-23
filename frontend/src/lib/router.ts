import { createContext, useContext } from 'react';

// Single-file router for the prototype app shell. No URL coupling — history
// is in-memory. In DEV mode, #s=<route> deeplink allows specifying initial screen.
// Each route id maps to one screen component (declared in AppShell).

export type Route =
  | 'splash'
  | 'welcome'
  | 'privacy'
  | 'create-cat'
  | 'first-meet'
  | 'home-day'
  | 'home-night'
  | 'daily-check'
  | 'ai-chat'
  | 'recap-start'
  | 'chat-diary'
  | 'mood-finalize'
  | 'reward'
  | 'calendar'
  | 'diary-detail'
  | 'stats'
  | 'insights'
  | 'cat-room'
  | 'inventory'
  | 'report'
  | 'login'
  | 'settings'
  // 건강냥(Medlife) 통합 — BE-only 기능 신규 화면 (feat/healthcat-backend)
  | 'coach'
  | 'wellbeing'
  | 'byok'
  | 'health-chat';

export type NavApi = {
  go: (route: Route) => void;       // push to history
  back: () => void;                  // pop one
  reset: (route: Route) => void;     // clear history, land on route
  current: Route;
  night: boolean;                    // time-of-day, resolved by the shell — home tab uses it at click time
  now: Date;
  nightOpenTime: string;
  nightTimezone: string;
  setNightOpenTime: (openTime: string, timezone: string) => void;
  wakeNightChat: () => void;
};

export const NavContext = createContext<NavApi>({
  go: () => undefined,
  back: () => undefined,
  reset: () => undefined,
  current: 'splash',
  night: true,
  now: new Date(),
  nightOpenTime: '19:00',
  nightTimezone: 'Asia/Seoul',
  setNightOpenTime: () => undefined,
  wakeNightChat: () => undefined,
});

export const useNav = () => useContext(NavContext);
