import { useCallback, useEffect, useRef, useState } from 'react';
import { Route, useNav } from '../lib/router';
import { MOOD_LABEL, Mood } from '../lib/store';

// ── Sketch UI primitives — bartender/barista coffee tone ─────────────────────

type TabKey = 'cal' | 'stat' | 'home' | 'cat' | 'ins';

// Tab → route mapping. Center 'home' resolves at click time so day/night
// shell can pick S06 vs S07 based on the current time-of-day.
const TAB_ROUTE: Record<Exclude<TabKey, 'home'>, Route> = {
  cal: 'calendar',
  stat: 'stats',
  cat: 'cat-room',
  ins: 'insights',
};

// 뒤로가기 버튼 — 전 화면 span.nav-arrow·인라인 ‹ 승격 공용 컴포넌트(A11Y-02).
// .nav-arrow(터치 타깃 44px ::before) 그대로 재사용 + .as-button(sketch.css)로 UA 버튼 크롬 제거.
export const BackButton = ({ onClick, tone }: { onClick: () => void; tone?: string }) => (
  <button
    type="button"
    className="nav-arrow as-button"
    aria-label="뒤로"
    onClick={onClick}
    style={tone ? { color: tone } : undefined}
  >
    ‹
  </button>
);

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
          aria-label={t.label}
          aria-current={t.k === active ? 'page' : undefined}
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
          <div className={'tab-icon' + (t.center ? ' tab-icon-lg' : '')} aria-hidden="true">{t.icon}</div>
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

// Tamaya 고양이 집사 캐릭터 — Figma "Tamaya v3" 정본 아트워크(3D 렌더 PNG).
// 2026-06-14: 손그림 SVG → Figma export 에셋으로 교체. props(size·mood·sleeping)는
// 호환 위해 유지하되, 이미지 아트라 color/accent/accessory 는 무시한다.
const CHAR_BASE = '/character/base.webp';      // 기본 전신(안경+조끼+나비넥타이)
const CHAR_SLEEPY = '/character/sleepy.webp';  // 졸린 표정(머리)

export const CatSketch = ({ size = 110, sleeping = false }: CatProps) => (
  <img
    src={sleeping ? CHAR_SLEEPY : CHAR_BASE}
    alt="이음이"
    width={size}
    height={size}
    style={{
      width: size,
      height: size,
      objectFit: 'contain',
      display: 'inline-block',
      userSelect: 'none',
      pointerEvents: 'none',
    }}
    draggable={false}
  />
);

// 감정 표정 아이콘 — Mood(이모지 키) → Figma 표정 에셋. 기존 emoji span 대체.
const MOOD_SRC: Record<string, string> = {
  '\u{1F60C}': '/character/calm.webp',   // 😌 평온
  '\u{1F60A}': '/character/happy.webp',  // 😊 기쁨
  '\u{1F623}': '/character/sleepy.webp', // 😣 힘듦/지침
  '\u{1F622}': '/character/sad.webp',    // 😢 슬픔
  '\u{1F621}': '/character/angry.webp',  // 😡 화남
};
export const MoodFace = ({ mood, size = 28 }: { mood: string; size?: number }) => (
  <img
    src={MOOD_SRC[mood] ?? MOOD_SRC['\u{1F60C}']}
    alt={MOOD_LABEL[mood as Mood] ?? '감정'}
    width={size}
    height={size}
    style={{
      width: size,
      height: size,
      objectFit: 'contain',
      display: 'inline-block',
      verticalAlign: 'middle',
      userSelect: 'none',
      pointerEvents: 'none',
    }}
    draggable={false}
  />
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
        fontFamily: 'Pretendard',
        fontSize: 11,
        color: 'var(--pencil)',
        background: 'var(--paper)',
        padding: '2px 6px',
        border: '1px dashed var(--ink)',
        borderRadius: 4,
      }}
    >
      {label}
    </span>
  </div>
);

// 토스트 훅 — 화면마다 복제되던 로컬 flash(setToast + setTimeout 1400)를 통합(Q9/PERF-07).
// 연타로 flash 가 연속 호출되면 이전 타이머를 clearTimeout 으로 취소해, 앞선 타이머가
// 뒤 토스트를 조기 소거하던 경합을 없앤다. 렌더(role="status" toast div)는 각 화면 유지.
export function useToast(): { toast: string | null; flash: (msg: string) => void } {
  const [toast, setToast] = useState<string | null>(null);
  const timerRef = useRef<number | undefined>(undefined);
  const flash = useCallback((msg: string) => {
    if (timerRef.current !== undefined) window.clearTimeout(timerRef.current);
    setToast(msg);
    timerRef.current = window.setTimeout(() => {
      setToast(null);
      timerRef.current = undefined;
    }, 1400);
  }, []);
  useEffect(
    () => () => {
      if (timerRef.current !== undefined) window.clearTimeout(timerRef.current);
    },
    [],
  );
  return { toast, flash };
}
