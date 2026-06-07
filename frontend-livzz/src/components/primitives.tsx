import { CSSProperties, ReactNode } from 'react';
import { Route, useNav } from '../lib/router';

// ── Sketch UI primitives — bartender/barista coffee tone ─────────────────────

export const StatusBar = ({ time = '11:42 PM', mode = 'night' }: { time?: string; mode?: 'day' | 'night' }) => (
  <div
    className="statusbar"
    style={{ background: mode === 'night' ? 'rgba(61,74,120,0.08)' : 'rgba(214,154,58,0.08)' }}
  >
    <span style={{ fontFamily: 'Patrick Hand' }}>{time}</span>
    <div className="notch" />
    <span style={{ fontFamily: 'Patrick Hand', display: 'flex', gap: 4, alignItems: 'center' }}>
      <span>{mode === 'night' ? '🌙' : '☀︎'}</span>
      <span>100%</span>
    </span>
  </div>
);

type TabKey = 'cal' | 'stat' | 'home' | 'cat' | 'ins';

// Tab → route mapping. Center 'home' resolves at click time so day/night
// shell can pick S06 vs S07 based on the current time-of-day.
const TAB_ROUTE: Record<Exclude<TabKey, 'home'>, Route> = {
  cal: 'calendar',
  stat: 'stats',
  cat: 'cat-room',
  ins: 'insights',
};

export const TabBar = ({
  active = 'home',
  onHome,
}: {
  active?: TabKey;
  onHome?: () => void; // shell picks home-day vs home-night
}) => {
  const nav = useNav();
  const tabs: { k: TabKey; label: string; icon: string; center?: boolean }[] = [
    { k: 'cal', label: '달력', icon: '▦' },
    { k: 'stat', label: '통계', icon: '▮' },
    { k: 'home', label: '홈', icon: '⌂', center: true },
    { k: 'cat', label: '키우기', icon: '◖' },
    { k: 'ins', label: '인사이트', icon: '✦' },
  ];
  const onTab = (k: TabKey) => {
    if (k === 'home') {
      // Resolve day/night at click time from the shell-provided time-of-day.
      if (onHome) onHome();
      else nav.go(nav.night ? 'home-night' : 'home-day');
      return;
    }
    nav.go(TAB_ROUTE[k]);
  };
  return (
    <div className="tabbar">
      {tabs.map((t) => (
        <button
          key={t.k}
          type="button"
          onClick={() => onTab(t.k)}
          className={'tab ' + (t.k === active ? 'active' : '') + (t.center ? ' tab-center' : '')}
          style={{
            background: 'transparent',
            border: 'none',
            cursor: 'pointer',
            fontFamily: 'inherit',
            color: 'inherit',
            padding: 0,
          }}
        >
          <div className={'tab-icon' + (t.center ? ' tab-icon-lg' : '')}>{t.icon}</div>
          <div>{t.label}</div>
        </button>
      ))}
    </div>
  );
};

type CatProps = {
  size?: number;
  mood?: 'awake' | 'happy' | 'wink';
  sleeping?: boolean;
  color?: string;
  accent?: string;
  accessory?: 'bowtie' | 'apron' | 'none';
};

// Hand-drawn barista butler cat — coffee tabby with bowtie
export const CatSketch = ({
  size = 110,
  mood = 'awake',
  sleeping = false,
  color = '#3a2414',
  accent = '#8c4a1f',
  accessory = 'bowtie',
}: CatProps) => {
  if (sleeping) {
    return (
      <svg width={size} height={size * 0.75} viewBox="0 0 140 100" fill="none">
        <path
          d="M20 70 Q 20 35 60 30 Q 110 25 122 55 Q 128 80 95 86 Q 60 90 30 85 Q 18 82 20 70 Z"
          stroke={color}
          strokeWidth="2"
          strokeLinejoin="round"
          fill="#f5e6cf"
        />
        <path
          d="M95 50 Q 110 48 118 56 Q 122 64 115 70 Q 108 74 100 70"
          stroke={color}
          strokeWidth="2"
          fill="#f5e6cf"
        />
        <path d="M100 50 L 96 42 L 105 48" stroke={color} strokeWidth="2" fill="none" />
        <path d="M112 50 L 116 42 L 118 50" stroke={color} strokeWidth="2" fill="none" />
        <path
          d="M104 62 Q 108 64 112 62"
          stroke={color}
          strokeWidth="2"
          fill="none"
          strokeLinecap="round"
        />
        <path d="M25 72 Q 5 72 8 50 Q 12 32 30 35" stroke={color} strokeWidth="2" fill="none" />
        <path
          d="M55 38 Q 70 36 85 40"
          stroke={accent}
          strokeWidth="1.2"
          fill="none"
          opacity="0.5"
        />
        <path
          d="M50 50 Q 70 48 90 52"
          stroke={accent}
          strokeWidth="1.2"
          fill="none"
          opacity="0.5"
        />
        <text x="60" y="22" fontFamily="Caveat" fontSize="18" fill={accent}>
          z z Z
        </text>
      </svg>
    );
  }
  return (
    <svg width={size} height={size} viewBox="0 0 120 120" fill="none">
      <path
        d="M28 38 L 22 12 L 46 28"
        stroke={color}
        strokeWidth="2"
        strokeLinejoin="round"
        fill="#f5e6cf"
      />
      <path
        d="M92 38 L 98 12 L 74 28"
        stroke={color}
        strokeWidth="2"
        strokeLinejoin="round"
        fill="#f5e6cf"
      />
      <path d="M30 30 L 28 18 L 38 26" stroke={accent} strokeWidth="1.5" fill="none" />
      <path d="M90 30 L 92 18 L 82 26" stroke={accent} strokeWidth="1.5" fill="none" />
      <ellipse cx="60" cy="56" rx="36" ry="32" stroke={color} strokeWidth="2" fill="#f5e6cf" />
      <path
        d="M40 32 Q 44 36 42 42"
        stroke={accent}
        strokeWidth="1.5"
        fill="none"
        opacity="0.55"
      />
      <path
        d="M80 32 Q 76 36 78 42"
        stroke={accent}
        strokeWidth="1.5"
        fill="none"
        opacity="0.55"
      />
      <path d="M60 30 L 60 38" stroke={accent} strokeWidth="1.5" opacity="0.55" />
      {mood === 'happy' ? (
        <>
          <path
            d="M44 52 Q 48 46 52 52"
            stroke={color}
            strokeWidth="2"
            fill="none"
            strokeLinecap="round"
          />
          <path
            d="M68 52 Q 72 46 76 52"
            stroke={color}
            strokeWidth="2"
            fill="none"
            strokeLinecap="round"
          />
        </>
      ) : mood === 'wink' ? (
        <>
          <circle cx="48" cy="54" r="2.5" fill={color} />
          <path
            d="M68 54 Q 72 50 76 54"
            stroke={color}
            strokeWidth="2"
            fill="none"
            strokeLinecap="round"
          />
        </>
      ) : (
        <>
          <circle cx="48" cy="54" r="3" fill={color} />
          <circle cx="72" cy="54" r="3" fill={color} />
        </>
      )}
      <path d="M58 64 L 62 64 L 60 68 Z" fill={accent} stroke={color} strokeWidth="1.5" />
      <path
        d="M60 68 Q 54 74 50 70"
        stroke={color}
        strokeWidth="2"
        fill="none"
        strokeLinecap="round"
      />
      <path
        d="M60 68 Q 66 74 70 70"
        stroke={color}
        strokeWidth="2"
        fill="none"
        strokeLinecap="round"
      />
      <path d="M30 60 L 44 62" stroke={color} strokeWidth="1.5" />
      <path d="M30 66 L 44 66" stroke={color} strokeWidth="1.5" />
      <path d="M90 60 L 76 62" stroke={color} strokeWidth="1.5" />
      <path d="M90 66 L 76 66" stroke={color} strokeWidth="1.5" />
      <path
        d="M32 86 Q 36 102 60 102 Q 84 102 88 86"
        stroke={color}
        strokeWidth="2"
        fill="#f5e6cf"
      />
      {accessory === 'bowtie' && (
        <g>
          <path
            d="M52 90 L 46 86 L 46 96 L 52 92 Z"
            fill={accent}
            stroke={color}
            strokeWidth="1.5"
            strokeLinejoin="round"
          />
          <path
            d="M68 90 L 74 86 L 74 96 L 68 92 Z"
            fill={accent}
            stroke={color}
            strokeWidth="1.5"
            strokeLinejoin="round"
          />
          <circle cx="60" cy="91" r="3" fill={accent} stroke={color} strokeWidth="1.5" />
        </g>
      )}
      {accessory === 'apron' && (
        <path
          d="M44 92 Q 60 96 76 92 L 78 108 L 42 108 Z"
          fill="#f5e6cf"
          stroke={color}
          strokeWidth="1.5"
          strokeLinejoin="round"
        />
      )}
    </svg>
  );
};

export const HandArrow = ({
  rotate = 0,
  length = 60,
  color = '#8c4a1f',
}: {
  rotate?: number;
  length?: number;
  color?: string;
}) => (
  <svg
    width={length}
    height="24"
    viewBox={`0 0 ${length} 24`}
    style={{ transform: `rotate(${rotate}deg)` }}
  >
    <path
      d={`M2 12 Q ${length / 3} 4 ${length - 12} 12`}
      stroke={color}
      strokeWidth="1.5"
      fill="none"
    />
    <path
      d={`M${length - 16} 6 L ${length - 10} 12 L ${length - 18} 16`}
      stroke={color}
      strokeWidth="1.5"
      fill="none"
      strokeLinecap="round"
      strokeLinejoin="round"
    />
  </svg>
);

export const ImgPh = ({
  w = '100%',
  h = 80,
  label = 'image',
}: {
  w?: number | string;
  h?: number | string;
  label?: string;
}) => (
  <div
    className="ph-stripe"
    style={{
      width: w,
      height: h,
      borderRadius: 8,
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
    }}
  >
    <span
      style={{
        fontFamily: 'Patrick Hand',
        fontSize: 11,
        color: '#7a5634',
        background: '#f5e6cf',
        padding: '2px 6px',
        border: '1px dashed #3a2414',
        borderRadius: 4,
      }}
    >
      {label}
    </span>
  </div>
);

export const Callout = ({ children, style }: { children: ReactNode; style?: CSSProperties }) => (
  <div className="anno" style={style}>
    <span>↳</span>
    <span>{children}</span>
  </div>
);
