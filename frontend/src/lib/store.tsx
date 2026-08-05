import {
  ReactNode,
  createContext,
  useContext,
  useEffect,
  useReducer,
} from 'react';

// In-memory app state with localStorage persistence. No backend — every
// "AI reply" is local simulation. Resets to defaults on first load.

export type Personality = '차분한' | '수다쟁이' | '시크' | '다정한' | '장난꾸러기';
export type CatColor = '#f5e6cf' | '#d8a777' | '#a66838' | '#6b3e1f' | '#3a2414';
export type Mood = '😌' | '😊' | '😣' | '😢' | '😡';

export type ChatMsg = {
  role: 'bot' | 'user';
  text: string;
  hint?: string;
  chips?: string[];
};

// five: 5턴 대화 · free: 자유 대화(상한 = 백엔드 세션 캡 50턴). 3턴(short) 모드는 폐지됨.
export type ChatDiaryMode = 'five' | 'free';
export type GeneratedDiary = {
  diary_date?: string;
  title: string;
  content: string;
  emotion: string;
  satisfaction: number;
  keywords?: string[];
};

export type DiaryEntry = {
  day: number;            // legacy day number used by the prototype screens
  date?: string;           // YYYY-MM-DD. Older localStorage entries infer 2026-05-DD.
  moods: Mood[];           // primary + secondary feelings
  keywords: string[];
  body: string;            // generated diary
  // 루틴 라벨 → 체크 여부 스냅샷. 레거시 엔트리는 food/water/sleep/movement/sun 키.
  check: Partial<Record<string, boolean>>;
  tomorrow?: string;
  createdAt: number;
};

// ── 루틴 · 낮 기록(리스트업) ────────────────────────────────────────────────
// 카테고리 어휘는 온보딩 선택지 = 낮 메모 태그 = 루틴 그룹으로 공유한다.
// 키는 영문 enum, 화면 표기는 CATEGORY_LABEL 한 곳에서만 (표기 SSOT).
export const CATEGORIES = ['health', 'learning', 'cert', 'hobby'] as const;
export type Category = (typeof CATEGORIES)[number];

export const CATEGORY_LABEL: Record<Category, string> = {
  health: '건강',
  learning: '학습',
  cert: '자격증',
  hobby: '취미',
};

export type Routine = { id: string; label: string; emoji: string; category: Category };
export type DayMemo = { id: string; text: string; category: Category };
// 하루 단위 낮 기록 — date가 오늘이 아니면 소비처에서 dayLogFor()로 리셋해 읽는다.
export type DayLog = { date: string; checks: Record<string, boolean>; memos: DayMemo[] };

// 각 카테고리 앞 3개 = 기본 12건(DEFAULT_ROUTINES), 나머지는 [관리]·추천의 제안 후보.
export const ROUTINE_PRESETS: Record<Category, { label: string; emoji: string }[]> = {
  health: [
    { label: '물 6컵 마시기', emoji: '💧' },
    { label: '30분 걷기', emoji: '🚶' },
    { label: '스트레칭 5분', emoji: '🤸' },
    { label: '12시 전에 자기', emoji: '😴' },
    { label: '아침 챙겨 먹기', emoji: '🍚' },
  ],
  learning: [
    { label: '30분 독서', emoji: '📖' },
    { label: '오늘 배운 것 한 줄 정리', emoji: '✍️' },
    { label: '영어 단어 10개', emoji: '🔤' },
    { label: '강의 노트 다시 보기', emoji: '📚' },
    { label: '관심 분야 글 하나 읽기', emoji: '📰' },
  ],
  cert: [
    { label: '기출문제 5문제', emoji: '✅' },
    { label: '인강 1강 듣기', emoji: '🎧' },
    { label: '오답노트 정리', emoji: '📒' },
    { label: '개념 한 챕터 훑기', emoji: '📗' },
    { label: '시험 일정 확인', emoji: '🗓️' },
  ],
  hobby: [
    { label: '좋아하는 일 15분', emoji: '🎨' },
    { label: '새로운 것 하나 시도', emoji: '✨' },
    { label: '오늘의 감상 한 줄', emoji: '🎵' },
    { label: '사진 한 장 남기기', emoji: '📷' },
    { label: '좋아하는 음악 한 곡', emoji: '🎼' },
  ],
};

// 기본 루틴 12건 = 4 카테고리 × 3. id는 고정(마이그레이션·중복 판정 기준).
const DEFAULT_ROUTINES_BY_CATEGORY: Record<Category, Routine[]> = Object.fromEntries(
  CATEGORIES.map((cat) => [
    cat,
    ROUTINE_PRESETS[cat].slice(0, 3).map((p, i) => ({
      id: `r-${cat}-${i}`,
      label: p.label,
      emoji: p.emoji,
      category: cat,
    })),
  ]),
) as Record<Category, Routine[]>;

export const DEFAULT_ROUTINES: Routine[] = CATEGORIES.flatMap(
  (cat) => DEFAULT_ROUTINES_BY_CATEGORY[cat],
);

// 기본 12건은 항상 시드하고, 고른 관심사 카테고리를 앞으로 당겨 보여준다.
// (관심사는 "무엇을 지울지"가 아니라 "무엇을 먼저 볼지"만 정한다 — 강요 0.)
export const seedRoutines = (interests: Category[]): Routine[] => {
  const ordered: Category[] = [
    ...interests.filter((c) => CATEGORIES.includes(c)),
    ...CATEGORIES.filter((c) => !interests.includes(c)),
  ];
  return ordered.flatMap((cat) => DEFAULT_ROUTINES_BY_CATEGORY[cat]);
};

// 커스텀 루틴 이모지 후보 — 별도 라이브러리 없이 고르기만.
export const ROUTINE_EMOJIS = [
  '💧', '🚶', '🤸', '🍚', '😴',
  '📖', '✍️', '🔤', '📚', '📰',
  '✅', '🎧', '📒', '📗', '🗓️',
  '🎨', '✨', '🎵', '📷', '☑️',
];

// v2 = 한글 카테고리(건강/스터디/취미/생활) → 영문 4분류 + 기본 12건 시드.
const ROUTINE_SCHEMA_VERSION = 2;

// 구버전 저장값 → 신 카테고리. '생활'(정리·지출 등 일상 활동)은 취미로 흡수한다.
const LEGACY_CATEGORY: Record<string, Category> = {
  건강: 'health',
  스터디: 'learning',
  취미: 'hobby',
  생활: 'hobby',
};

export const toCategory = (value: unknown): Category =>
  CATEGORIES.includes(value as Category)
    ? (value as Category)
    : LEGACY_CATEGORY[String(value)] ?? 'health';

// ── 4 카테고리 그룹핑 (표시 SSOT) ──────────────────────────────────────────
// 순서(건강→학습→자격증→취미)와 라벨을 여기 한 곳에서만 정한다. 낮 홈·밤 홈(S06/S07)·
// 낮 기록(S08)·저녁 회고(S10)가 전부 이 헬퍼를 통해 그리므로 화면마다 순서가 갈리지 않는다.
// category 값은 toCategory로 흡수 — 구버전 저장값이 섞여도 4 그룹 밖으로 새지 않는다.
export type CategoryGroup<T> = { category: Category; label: string; items: T[] };

export const groupByCategory = <T extends { category: Category }>(
  items: T[],
): CategoryGroup<T>[] =>
  CATEGORIES.map((category) => ({
    category,
    label: CATEGORY_LABEL[category],
    items: items.filter((item) => toCategory(item.category) === category),
  }));

// 그룹 헤더 없이 순서만 맞출 때 (일기 체크 스냅샷 등) — 합계·집계는 불변, 나열 순서만 정렬.
export const sortByCategory = <T extends { category: Category }>(items: T[]): T[] =>
  groupByCategory(items).flatMap((group) => group.items);

const todayKeyOf = (now: Date = new Date()) =>
  `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}-${String(now.getDate()).padStart(2, '0')}`;

const emptyDayLog = (now: Date = new Date()): DayLog => ({
  date: todayKeyOf(now),
  checks: {},
  memos: [],
});

// 날짜가 넘어간 dayLog는 빈 오늘 기록으로 취급 (읽기 전용 파생 — 리듀서는 쓰기 시점에 리셋).
export const dayLogFor = (log: DayLog, now: Date = new Date()): DayLog =>
  log.date === todayKeyOf(now) ? log : emptyDayLog(now);

export type State = {
  character: { name: string; color: CatColor; personalities: Personality[] };
  schemaVersion?: number;      // 루틴 카테고리 스키마 버전 (마이그레이션 1회 실행용)
  interests: Category[];       // 온보딩에서 선택 — 루틴 노출 순서·메모 태그와 어휘 공유
  routines: Routine[];         // 사용자 루틴 (가변, 커스터마이징 가능)
  dayLog: DayLog;              // 오늘의 낮 기록 — 루틴 체크 + 메모
  chatDiary: ChatMsg[];
  chatDiaryMode: ChatDiaryMode;
  chatDiaryMaxTurns: 5 | 50;
  chatDiaryGeneratedDiary: GeneratedDiary | null;
  diaries: DiaryEntry[];
  selectedDay: number | null;       // legacy fallback for older screens
  selectedDate: string | null;      // 달력에서 선택한 날짜 → 일기 디테일이 읽음
  points: number;
  streak: number;
  level: number;
  unlockedItems: string[];
  equippedItem: string | null;
};

// ── Seed diary data (on-device) ─────────────────────────────────────────────
// 달력·통계·일기 디테일이 실제 데이터에 연동되도록 5월 한 달치 시드.
// 원문은 기기 내(localStorage)에만 — liv-I1 Private-First 정합(서버 DB 미사용).
const mk = (
  day: number,
  primary: Mood,
  sec: Mood[],
  keywords: string[],
  body: string,
  checks: string, // F=식사 W=물 S=수면 M=운동 U=햇볕
  tomorrow: string,
): DiaryEntry => ({
  day,
  moods: [primary, ...sec],
  keywords,
  body: `5월 ${day}일. ${body}`,
  check: {
    food: checks.includes('F'),
    water: checks.includes('W'),
    sleep: checks.includes('S'),
    movement: checks.includes('M'),
    sun: checks.includes('U'),
  },
  tomorrow,
  createdAt: Date.UTC(2026, 4, day, 13, 0),
  date: `2026-05-${String(day).padStart(2, '0')}`,
});

const SEED_DIARIES: DiaryEntry[] = [
  mk(2, '😌', ['😊'], ['주말', '산책', '햇살'], '늦잠 자고 동네 한 바퀴. 햇살이 좋아서 마음이 풀렸다.', 'FWMU', '아침 스트레칭 10분'),
  mk(3, '😊', [], ['친구', '커피', '수다'], '오랜만에 친구랑 커피. 웃을 일이 많았던 하루.', 'FWS', '물 6잔 채우기'),
  mk(5, '😣', ['😌'], ['마감', '야근', '피곤'], '마감 때문에 늦게까지 일했다. 어깨가 무거웠다.', 'FW', '점심은 따뜻한 국물로'),
  mk(7, '😊', ['😌'], ['운동', '산책', '개운'], '저녁에 30분 걸었더니 머리가 맑아졌다.', 'FWSMU', '같은 시간에 또 걷기'),
  mk(9, '😌', [], ['집정리', '여유', '차'], '집을 정리하고 차 한 잔. 조용한 게 좋았다.', 'FWS', '책 10쪽 읽기'),
  mk(10, '😢', ['😣'], ['외로움', '비', '생각'], '비 오는 날, 괜히 마음이 가라앉았다.', 'F', '내일은 누군가에게 안부 묻기'),
  mk(12, '😊', ['😌'], ['칭찬', '성취', '점심'], '맡은 일이 잘 풀렸고 칭찬도 들었다. 뿌듯.', 'FWSU', '잘한 일 한 줄 적기'),
  mk(13, '😌', [], ['루틴', '물', '안정'], '평범했지만 루틴을 다 지킨 하루.', 'FWSM', '수면 12시 전'),
  mk(15, '😡', ['😣'], ['갈등', '회의', '답답'], '회의에서 의견이 부딪혀 답답했다.', 'FW', '감정 식히고 메모로 정리'),
  mk(16, '😣', ['😌'], ['수면부족', '커피', '버팀'], '잠을 못 자 하루 종일 멍했다.', 'FWU', '카페인 오후 2시 전까지'),
  mk(18, '😌', ['😊'], ['휴식', '음악', '회복'], '아무것도 안 하고 음악만 들었다. 회복되는 느낌.', 'FWS', '가벼운 산책'),
  mk(19, '😊', [], ['약속', '맛집', '기분좋음'], '맛집 다녀오고 기분이 좋아졌다.', 'FWMU', '물 더 마시기'),
  mk(20, '😊', ['😌'], ['집중', '몰입', '뿌듯'], '오전 내내 몰입해서 일했다. 시간 가는 줄 몰랐다.', 'FWS', '눈 휴식 자주'),
  mk(21, '😌', [], ['산책', '햇볕', '평온'], '점심 후 햇볕 쐬며 걸었다. 평온했다.', 'FWSMU', '같은 산책 반복'),
  mk(22, '😣', ['😢'], ['피곤', '무기력', '늦잠'], '몸이 무거워 아무것도 손에 안 잡혔다.', 'FW', '일찍 자기'),
  mk(23, '😊', ['😌'], ['회복', '운동', '개운'], '다시 움직였더니 컨디션이 올라왔다.', 'FWSMU', '스트레칭 유지'),
  mk(24, '😌', ['😊'], ['주말', '느긋', '책'], '느긋하게 책 읽은 주말. 충전된 느낌.', 'FWS', '내일 일정 가볍게'),
  mk(25, '😣', ['😌'], ['업무', '집중', '피로'], '집중은 잘됐지만 끝나니 진이 빠졌다.', 'FWU', '저녁에 10분 산책'),
  mk(26, '😣', ['😌', '😊'], ['긴 회의', '우동', '5분이 없음'], '점심으로 우동 한 그릇이 위로였다. 긴 회의로 피곤했고, 끝난 뒤 숨 돌릴 5분이 없었던 게 무거웠다.', 'FWU', '회의 종료 후 · 3분 호흡 알람'),
];

const DEFAULT_STATE: State = {
  character: { name: '이음이', color: '#a66838', personalities: ['다정한'] },
  schemaVersion: ROUTINE_SCHEMA_VERSION,
  interests: ['health'],
  routines: seedRoutines(['health']),
  dayLog: emptyDayLog(),
  chatDiary: [],
  chatDiaryMode: 'five',
  chatDiaryMaxTurns: 5,
  chatDiaryGeneratedDiary: null,
  diaries: SEED_DIARIES,
  selectedDay: 26,
  selectedDate: '2026-05-26',
  points: 240,
  streak: 12,
  level: 3,
  unlockedItems: ['🧣 스카프', '👕 줄무늬'],
  equippedItem: '👕 줄무늬',
};

type Action =
  | { type: 'character/set'; patch: Partial<State['character']> }
  | { type: 'interests/set'; interests: Category[] }
  | { type: 'routine/add'; label: string; emoji?: string; category: Category }
  | { type: 'routine/update'; id: string; label: string; emoji: string; category: Category }
  | { type: 'routine/remove'; id: string }
  | { type: 'routine/toggle'; id: string }
  | { type: 'memo/add'; text: string; category: Category }
  | { type: 'memo/remove'; id: string }
  | { type: 'chat-diary/configure'; mode: ChatDiaryMode; maxTurns: 5 | 50 }
  | { type: 'chat-diary/append'; msg: ChatMsg }
  | { type: 'chat-diary/set-generated-diary'; diary: GeneratedDiary | null }
  | { type: 'chat-diary/reset' }
  | { type: 'diary/save'; entry: DiaryEntry }
  | { type: 'diaries/merge'; entries: DiaryEntry[] }
  | { type: 'ui/select-day'; day: number }
  | { type: 'ui/select-date'; date: string }
  | { type: 'points/add'; delta: number }
  | { type: 'streak/inc' }
  | { type: 'item/equip'; item: string }
  | { type: 'item/unlock'; item: string }
  | { type: 'state/replace'; state: State };

const pad2 = (n: number) => String(n).padStart(2, '0');

export function diaryDateOf(entry: Pick<DiaryEntry, 'day' | 'date'>): string {
  return entry.date ?? `2026-05-${pad2(entry.day)}`;
}

export const dateParts = (date: string) => {
  const [year, month, day] = date.split('-').map(Number);
  return { year, month, day };
};

function reducer(state: State, action: Action): State {
  switch (action.type) {
    case 'character/set':
      return { ...state, character: { ...state.character, ...action.patch } };
    case 'interests/set': {
      // 온보딩 전용 — 기본 12건을 관심사 순으로 다시 시드하되, 사용자가 만든 루틴은 보존한다.
      // 라벨도 dedup — v1 마이그레이션을 거친 루틴은 구 id(r-건강-0)라 id만으로는 기본 시드와
      // 같은 라벨이 중복 합류할 수 있다 (체크 스냅샷이 라벨 키라 라벨 중복은 불변식 위반).
      const seeded = seedRoutines(action.interests);
      const seededIds = new Set(seeded.map((r) => r.id));
      const seededLabels = new Set(seeded.map((r) => r.label));
      const custom = state.routines.filter(
        (r) => !seededIds.has(r.id) && !seededLabels.has(r.label),
      );
      return { ...state, interests: action.interests, routines: [...seeded, ...custom] };
    }
    case 'routine/add': {
      const label = action.label.trim();
      if (!label || state.routines.some((r) => r.label === label)) return state;
      const routine: Routine = {
        id: `r-user-${Date.now()}`,
        label,
        emoji: action.emoji ?? '☑️',
        category: action.category,
      };
      return { ...state, routines: [...state.routines, routine] };
    }
    case 'routine/update': {
      const label = action.label.trim();
      if (!label) return state;
      // 다른 루틴과 이름이 겹치면 무시 (체크 스냅샷이 라벨 기준이라 중복 금지).
      if (state.routines.some((r) => r.id !== action.id && r.label === label)) return state;
      return {
        ...state,
        routines: state.routines.map((r) =>
          r.id === action.id ? { ...r, label, emoji: action.emoji || r.emoji, category: action.category } : r,
        ),
      };
    }
    case 'routine/remove': {
      const log = dayLogFor(state.dayLog);
      const { [action.id]: _removed, ...checks } = log.checks;
      return {
        ...state,
        routines: state.routines.filter((r) => r.id !== action.id),
        dayLog: { ...log, checks },
      };
    }
    case 'routine/toggle': {
      const log = dayLogFor(state.dayLog);
      return {
        ...state,
        dayLog: { ...log, checks: { ...log.checks, [action.id]: !log.checks[action.id] } },
      };
    }
    case 'memo/add': {
      const text = action.text.trim();
      if (!text) return state;
      const log = dayLogFor(state.dayLog);
      const memo: DayMemo = { id: `m-${Date.now()}`, text, category: action.category };
      return { ...state, dayLog: { ...log, memos: [...log.memos, memo] } };
    }
    case 'memo/remove': {
      const log = dayLogFor(state.dayLog);
      return { ...state, dayLog: { ...log, memos: log.memos.filter((m) => m.id !== action.id) } };
    }
    case 'chat-diary/configure':
      return {
        ...state,
        chatDiaryMode: action.mode,
        chatDiaryMaxTurns: action.maxTurns,
      };
    case 'chat-diary/append':
      return { ...state, chatDiary: [...state.chatDiary, action.msg] };
    case 'chat-diary/set-generated-diary':
      return { ...state, chatDiaryGeneratedDiary: action.diary };
    case 'chat-diary/reset':
      return { ...state, chatDiary: [], chatDiaryGeneratedDiary: null };
    case 'diary/save':
      const saveDate = diaryDateOf(action.entry);
      return {
        ...state,
        diaries: [...state.diaries.filter((d) => diaryDateOf(d) !== saveDate), action.entry],
        selectedDay: action.entry.day,
        selectedDate: saveDate,
      };
    case 'diaries/merge': {
      // 서버 엔트리로 로컬 풍부 엔트리를 통째로 덮어쓰지 않고 필드 단위로 병합한다.
      // 로컬에만 있는 check(라이프체크)·tomorrow(내일 다짐)·복합 moods 는 보존하고,
      // body/keywords 등 서버가 갱신한 필드는 받아들인다.
      const byDate = new Map(state.diaries.map((d) => [diaryDateOf(d), d]));
      action.entries.forEach((entry) => {
        const key = diaryDateOf(entry);
        const local = byDate.get(key);
        byDate.set(
          key,
          local
            ? {
                ...local,
                ...entry,
                check: local.check ?? entry.check,
                tomorrow: local.tomorrow ?? entry.tomorrow,
                moods:
                  (local.moods?.length ?? 0) > (entry.moods?.length ?? 0)
                    ? local.moods
                    : entry.moods,
              }
            : entry,
        );
      });
      return {
        ...state,
        diaries: [...byDate.values()].sort((a, b) => diaryDateOf(a).localeCompare(diaryDateOf(b))),
      };
    }
    case 'ui/select-day':
      return { ...state, selectedDay: action.day };
    case 'ui/select-date': {
      const entry = entryForDate(state.diaries, action.date);
      return { ...state, selectedDate: action.date, selectedDay: entry?.day ?? null };
    }
    case 'points/add':
      return { ...state, points: state.points + action.delta };
    case 'streak/inc':
      return { ...state, streak: state.streak + 1 };
    case 'item/equip':
      return { ...state, equippedItem: action.item };
    case 'item/unlock':
      return {
        ...state,
        unlockedItems: state.unlockedItems.includes(action.item)
          ? state.unlockedItems
          : [...state.unlockedItems, action.item],
      };
    case 'state/replace':
      return action.state;
    default:
      return state;
  }
}

const LS_KEY = 'tamaya-state-v2'; // v2: 시드 일기 + selectedDay 추가 (구버전 자동 리셋)

// ── 계정별 로컬 상태 경계 ────────────────────────────────────────────────────
// 로컬 상태(LS_KEY)는 브라우저당 1개 blob이라 계정과 무관하게 이어진다.
// 시드 데모 데이터(DEFAULT_STATE)는 비로그인 데모 전용으로 남기고, 실계정은
// 빈 상태에서 시작한다. 상태의 주인(닉네임)을 별도 키에 기록해 두고, 다른
// 계정 로그인 시 이전 사용자의 상태가 보이지 않도록 리셋 판정에 쓴다.
const OWNER_KEY = 'tamaya-state-owner';

/** 실계정 첫 시작용 빈 상태 — 시드 일기·포인트·스트릭·보상 없음. */
export const emptyAccountState = (): State => ({
  ...DEFAULT_STATE,
  routines: seedRoutines(['health']), // 온보딩 관심사 선택이 다시 시드한다.
  dayLog: emptyDayLog(),
  diaries: [],
  selectedDay: null,
  selectedDate: null,
  points: 0,
  streak: 0,
  level: 1,
  unlockedItems: [],
  equippedItem: null,
});

/** 현 로컬 상태의 주인 닉네임 (기록 전이면 null). */
export const getStateOwner = (): string | null => {
  try {
    return localStorage.getItem(OWNER_KEY);
  } catch {
    return null;
  }
};

export const setStateOwner = (nickname: string): void => {
  try {
    localStorage.setItem(OWNER_KEY, nickname);
  } catch {
    // ignore quota/unavailable
  }
};

// 완전삭제(purge) 진행 중 persist 억제 — beforeunload/visibilitychange flush(PERF-04)가
// localStorage.removeItem 직후의 reload 사이에 끼어들어 인메모리 state를 재기록,
// 삭제를 되돌리는 것을 방지한다 (liv-I1 완전 삭제 보증).
let persistSuppressed = false;
export const suppressPersistence = () => {
  persistSuppressed = true;
};

// 저장된 구버전 state → 현 스키마. 사용자가 쌓은 일기·체크·커스텀 루틴은 절대 버리지 않는다.
const migrateState = (saved: State, savedVersion: number | undefined): State => {
  const routines: Routine[] = (saved.routines ?? []).map((r) => ({
    ...r,
    category: toCategory(r.category),
  }));
  const interests = Array.from(new Set((saved.interests ?? []).map(toCategory)));
  const dayLog = saved.dayLog
    ? {
        ...saved.dayLog,
        memos: (saved.dayLog.memos ?? []).map((m) => ({ ...m, category: toCategory(m.category) })),
      }
    : saved.dayLog;

  // 기본 12건은 스키마 승격 시 1회만 합류시킨다 (이후 사용자가 지운 건 다시 살아나지 않음).
  // 버전은 반드시 "저장된 값"으로 판정한다 — DEFAULT_STATE와 머지된 뒤엔 항상 최신값이라 무의미.
  let merged = routines;
  if (savedVersion !== ROUTINE_SCHEMA_VERSION) {
    const haveIds = new Set(routines.map((r) => r.id));
    const haveLabels = new Set(routines.map((r) => r.label));
    const missing = DEFAULT_ROUTINES.filter((d) => !haveIds.has(d.id) && !haveLabels.has(d.label));
    merged = [...routines, ...missing];
  }

  return {
    ...saved,
    schemaVersion: ROUTINE_SCHEMA_VERSION,
    interests: interests.length > 0 ? interests : ['health'],
    routines: merged,
    dayLog: dayLog ?? emptyDayLog(),
  };
};

const StoreContext = createContext<{
  state: State;
  dispatch: React.Dispatch<Action>;
}>({ state: DEFAULT_STATE, dispatch: () => undefined });

export const StoreProvider = ({ children }: { children: ReactNode }) => {
  const [state, dispatch] = useReducer(reducer, DEFAULT_STATE, (init) => {
    try {
      const raw = localStorage.getItem(LS_KEY);
      if (raw) {
        const parsed = JSON.parse(raw) as Partial<State>;
        const saved = { ...init, ...parsed } as State;
        // 레거시 모드 마이그레이션: full(50턴)→free, short(3턴 폐지)→five.
        // maxTurns는 항상 mode에서 다시 유도해 저장값 불일치를 흡수한다.
        const legacyMode = saved.chatDiaryMode as string;
        if (legacyMode === 'full') saved.chatDiaryMode = 'free';
        else if (legacyMode === 'short') saved.chatDiaryMode = 'five';
        saved.chatDiaryMaxTurns =
          saved.chatDiaryMode === 'free' ? CHAT_DIARY_FREE_TURNS : CHAT_DIARY_FIVE_TURNS;
        return migrateState(saved, parsed.schemaVersion);
      }
    } catch {
      // ignore parse errors
    }
    return init;
  });

  // 저장 debounce(300ms) — 매 dispatch 마다 동기 JSON.stringify→localStorage 하던 것을
  // 마지막 변경 뒤 한 번만 쓴다. 유실 방지: 탭 백그라운드(visibilitychange hidden)·
  // 페이지 종료(beforeunload) 시점에 대기 중 저장을 즉시 flush 한다 (PERF-04).
  useEffect(() => {
    const persist = () => {
      if (persistSuppressed) return;
      try {
        localStorage.setItem(LS_KEY, JSON.stringify(state));
      } catch {
        // ignore quota
      }
    };
    const timer = window.setTimeout(persist, 300);
    const flush = () => {
      if (persistSuppressed) return;
      window.clearTimeout(timer);
      persist();
    };
    const onVisibility = () => {
      if (document.visibilityState === 'hidden') flush();
    };
    window.addEventListener('beforeunload', flush);
    document.addEventListener('visibilitychange', onVisibility);
    return () => {
      window.clearTimeout(timer);
      window.removeEventListener('beforeunload', flush);
      document.removeEventListener('visibilitychange', onVisibility);
    };
  }, [state]);

  return (
    <StoreContext.Provider value={{ state, dispatch }}>
      {children}
    </StoreContext.Provider>
  );
};

export const useStore = () => useContext(StoreContext);

// ── ChatDiary 회고 시퀀스 ────────────────────────────────────────────────

export const CHAT_DIARY_FREE_TURNS = 50; // 자유 모드 — 백엔드 세션 상한과 동일
export const CHAT_DIARY_FIVE_TURNS = 5;

export const CHAT_DIARY_TURNS: { question: string; hint?: string }[] = [
  {
    question: '오늘 하루 어땠어? 한 단어로 표현하면?',
    hint: '↳ 가장 강하게 남은 감정 한 단어',
  },
  {
    question: '그 감정이 가장 컸던 순간은 언제였어?',
    hint: '↳ 시간·장소·상황을 떠올려봐',
  },
  {
    question: '그때 누구랑 있었어? 아니면 혼자였어?',
  },
  {
    question: '오늘 가장 다행이었던 일은?',
    hint: '↳ 작아도 좋아 — 우동 한 그릇 같은 것도',
  },
  {
    question: '내일은 어떤 한 가지를 해보고 싶어?',
    hint: '↳ 알람으로 추가할 수 있어',
  },
];

export const CHAT_DIARY_INTRO: ChatMsg = {
  role: 'bot',
  text: '오늘도 고생했어.\n천천히 같이 정리해볼까?',
};

// ── 달력·통계 집계 (on-device diaries에서 파생) ────────────────────────────
export type Period = '주' | '월' | '전체';

export const MOODS_ALL: Mood[] = ['😌', '😊', '😣', '😢', '😡'];
export const MOOD_LABEL: Record<Mood, string> = {
  '😌': '평온',
  '😊': '기쁨',
  '😣': '피곤',
  '😢': '슬픔',
  '😡': '짜증',
};
// 색 정본 = tokens.css --mood-* (값 1:1 정합) — 소비처(records.tsx background, moodPct
// color 필드) 전부 CSS 색 컨텍스트 확인됨(canvas 2D 등 var() 미해석 컨텍스트 없음).
export const MOOD_BAR: Record<Mood, string> = {
  '😌': 'var(--mood-calm)',
  '😊': 'var(--mood-joy)',
  '😣': 'var(--mood-tired)',
  '😢': 'var(--mood-sad)',
  '😡': 'var(--mood-irritated)',
};
export const WEEKDAY_KR = ['일', '월', '화', '수', '목', '금', '토'];
export const weekdayOfDate = (date: string) => new Date(`${date}T00:00:00`).getDay();

export const formatDateKey = (year: number, month: number, day: number) =>
  `${year}-${pad2(month)}-${pad2(day)}`;

export const formatMonthDay = (entry: DiaryEntry) => {
  const { month, day } = dateParts(diaryDateOf(entry));
  return `${month}월 ${day}일`;
};

export const monthKeyOf = (date: string) => date.slice(0, 7);

export const entryForDay = (diaries: DiaryEntry[], day: number | null) =>
  day == null ? undefined : diaries.find((d) => d.day === day);

export const entryForDate = (diaries: DiaryEntry[], date: string | null) =>
  date == null ? undefined : diaries.find((d) => diaryDateOf(d) === date);

export const latestEntry = (diaries: DiaryEntry[]) =>
  diaries.length
    ? [...diaries].sort((a, b) => diaryDateOf(b).localeCompare(diaryDateOf(a)))[0]
    : undefined;

export const entriesForMonth = (diaries: DiaryEntry[], year: number, month: number) => {
  const monthKey = `${year}-${pad2(month)}`;
  return diaries.filter((d) => monthKeyOf(diaryDateOf(d)) === monthKey);
};

export const moodByDate = (diaries: DiaryEntry[]): Record<string, Mood> => {
  const m: Record<string, Mood> = {};
  diaries.forEach((d) => {
    if (d.moods[0]) m[diaryDateOf(d)] = d.moods[0];
  });
  return m;
};

// '전체'에서만 더해지는 이전 달(4월) 누적 baseline — 월/전체가 구분되도록
const HISTORY = {
  count: 22,
  writeDays: 22,
  weekday: [2, 4, 5, 3, 4, 3, 1],
  mood: { '😌': 9, '😊': 6, '😣': 4, '😢': 2, '😡': 1 } as Record<Mood, number>,
  routine: { 식사: 19, 물: 15, 수면: 12, 운동: 9, 햇볕: 11 } as Record<string, number>,
};

// 시드/구버전 일기의 check 키(DailyKey) → 표시 라벨
const LEGACY_CHECK_LABEL: Record<string, string> = {
  food: '식사',
  water: '물',
  sleep: '수면',
  movement: '운동',
  sun: '햇볕',
};

export const checkLabelOf = (key: string) => LEGACY_CHECK_LABEL[key] ?? key;

export type StatsResult = {
  count: number;
  writeDays: number;
  weekday: number[];
  moodPct: { mood: Mood; label: string; pct: number; color: string }[];
  // 루틴 라벨별 체크된 일수 — 많이 지킨 순
  routines: { label: string; days: number }[];
};

// 실날짜 기준 "오늘 포함 최근 7일" 윈도우 판정. 레거시 TODAY_DAY=27(5월 고정)
// 프로토타입 상수를 대체 — 주간 카운트·주간 통계가 실제 오늘을 따라가도록 한다.
export const isWithinLastWeek = (
  entry: Pick<DiaryEntry, 'day' | 'date'>,
  now: Date = new Date(),
): boolean => {
  const entryKey = diaryDateOf(entry);
  const todayKey = formatDateKey(now.getFullYear(), now.getMonth() + 1, now.getDate());
  const start = new Date(now.getFullYear(), now.getMonth(), now.getDate() - 6);
  const startKey = formatDateKey(start.getFullYear(), start.getMonth() + 1, start.getDate());
  return entryKey >= startKey && entryKey <= todayKey;
};

export const statsFor = (diaries: DiaryEntry[], period: Period): StatsResult => {
  const filtered = period === '주' ? diaries.filter((d) => isWithinLastWeek(d)) : diaries;

  const weekday = [0, 0, 0, 0, 0, 0, 0];
  const mood: Record<Mood, number> = { '😌': 0, '😊': 0, '😣': 0, '😢': 0, '😡': 0 };
  const routineDays: Record<string, number> = {};
  filtered.forEach((d) => {
    weekday[weekdayOfDate(diaryDateOf(d))]++;
    if (d.moods[0]) mood[d.moods[0]]++;
    Object.entries(d.check ?? {}).forEach(([key, on]) => {
      if (!on) return;
      const label = checkLabelOf(key);
      routineDays[label] = (routineDays[label] ?? 0) + 1;
    });
  });
  let count = filtered.length;
  let writeDays = new Set(filtered.map((d) => d.day)).size;

  if (period === '전체') {
    count += HISTORY.count;
    writeDays += HISTORY.writeDays;
    HISTORY.weekday.forEach((v, i) => (weekday[i] += v));
    MOODS_ALL.forEach((m) => (mood[m] += HISTORY.mood[m]));
    Object.entries(HISTORY.routine).forEach(([label, v]) => {
      routineDays[label] = (routineDays[label] ?? 0) + v;
    });
  }

  const totalMood = MOODS_ALL.reduce((a, m) => a + mood[m], 0) || 1;
  const moodPct = MOODS_ALL.map((m) => ({
    mood: m,
    label: MOOD_LABEL[m],
    pct: Math.round((mood[m] / totalMood) * 100),
    color: MOOD_BAR[m],
  })).sort((a, b) => b.pct - a.pct);

  const routines = Object.entries(routineDays)
    .map(([label, days]) => ({ label, days }))
    .sort((a, b) => b.days - a.days)
    .slice(0, 6);

  return { count, writeDays, weekday, moodPct, routines };
};
