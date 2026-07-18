import { Mood, MOODS_ALL, MOOD_LABEL } from '../lib/store';
import { MoodFace } from './primitives';

// 감정 선택 소프트 팔레트 — 흩어진 이모지 나열 UI를 공용 컴포넌트로 승격(T3).
// 탭 1회 = 단일 선택. 색은 tokens.css --mood-* (C3 히트맵과 같은 SSOT) 만 참조 —
// 신규 색 발명 금지. allowSkip = 강요 없는 스킵(재즈: 빈도 벌점·끊김 문구 ❌).
// 데이터 shape 불변: Mood(이모지 키) 그대로, onChange 시그니처 = 기존 setter 정합.

// Mood → 감정 색 토큰. tokens.css --mood-* 5종과 1:1 (mood-heatmap 과 동일 매핑).
const MOOD_TOKEN: Record<Mood, string> = {
  '😌': 'var(--mood-calm)',
  '😊': 'var(--mood-joy)',
  '😣': 'var(--mood-tired)',
  '😢': 'var(--mood-sad)',
  '😡': 'var(--mood-irritated)',
};

type Props = {
  value: Mood | null;
  onChange: (mood: Mood) => void;
  allowSkip?: boolean;
  onSkip?: () => void;
  skipLabel?: string;
};

// 소프트 그라데이션 배경 — 감정 토큰을 paper 로 희석(선택=진하게·미선택=옅게).
// near-white 2종(😢/😡)도 ink 30% 파생 테두리로 배경과 구분(히트맵 규칙 승계).
const chipBackground = (token: string, selected: boolean): string =>
  selected
    ? `linear-gradient(135deg, color-mix(in srgb, ${token} 92%, var(--paper)) 0%, color-mix(in srgb, ${token} 58%, var(--paper)) 100%)`
    : `linear-gradient(135deg, color-mix(in srgb, ${token} 38%, var(--paper)) 0%, color-mix(in srgb, ${token} 20%, var(--paper)) 100%)`;

export const MoodPalette = ({
  value,
  onChange,
  allowSkip = false,
  onSkip,
  skipLabel = '건너뛰기',
}: Props) => (
  <div
    role="group"
    aria-label="감정 선택"
    style={{ display: 'flex', flexWrap: 'wrap', justifyContent: 'center', gap: 8 }}
  >
    {MOODS_ALL.map((mood) => {
      const selected = value === mood;
      const token = MOOD_TOKEN[mood];
      return (
        <button
          key={mood}
          type="button"
          className="chip mood-chip"
          aria-label={MOOD_LABEL[mood]}
          aria-pressed={selected}
          onClick={() => onChange(mood)}
          style={{
            background: chipBackground(token, selected),
            border: selected
              ? '2px solid var(--accent)'
              : `1.5px solid color-mix(in srgb, var(--ink) 30%, ${token})`,
            color: 'var(--ink)',
          }}
        >
          <MoodFace mood={mood} size={22} />
          <span>{MOOD_LABEL[mood]}</span>
        </button>
      );
    })}
    {allowSkip && onSkip && (
      <button
        type="button"
        className="chip dashed mood-chip mood-skip"
        aria-label={skipLabel}
        onClick={onSkip}
        style={{ color: 'var(--pencil)' }}
      >
        {skipLabel}
      </button>
    )}
  </div>
);
