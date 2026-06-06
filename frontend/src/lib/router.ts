import { createContext, useContext } from 'react';

// Single-file router for the prototype app shell. No URL coupling — history
// is in-memory; switching to design mode uses URL hash separately. Each route
// id maps to one screen component (declared in AppShell).

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
  | 'settings';

export type NavApi = {
  go: (route: Route) => void;       // push to history
  back: () => void;                  // pop one
  reset: (route: Route) => void;     // clear history, land on route
  current: Route;
  night: boolean;                    // time-of-day, resolved by the shell — home tab uses it at click time
};

export const NavContext = createContext<NavApi>({
  go: () => undefined,
  back: () => undefined,
  reset: () => undefined,
  current: 'splash',
  night: true,
});

export const useNav = () => useContext(NavContext);
