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

export type DiaryEntry = {
  day: number;            // 1..31 of current month for the prototype
  moods: Mood[];           // primary + secondary feelings
  keywords: string[];
  body: string;            // generated diary
  check: Partial<Record<DailyKey, boolean>>;
  tomorrow?: string;
  createdAt: number;
};

export type DailyKey = 'food' | 'water' | 'sleep' | 'movement' | 'sun';

export type State = {
  character: { name: string; color: CatColor; personalities: Personality[] };
  daily: {
    food: { done: boolean; picks: string[] };       // 아침/점심/저녁/간식
    water: number;                                   // 0..8
    sleep: { done: boolean; quality: string | null };
    movement: { done: boolean; bucket: string | null };
    sun: { done: boolean; level: string | null };
  };
  aiChat: ChatMsg[];
  chatDiary: ChatMsg[];
  diaries: DiaryEntry[];
  selectedDay: number | null;       // 달력에서 선택한 날 → 일기 디테일이 읽음
  points: number;
  streak: number;
  level: number;
  unlockedItems: string[];
  equippedItem: string | null;
};

const today = new Date();

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
  daily: {
    food: { done: false, picks: [] },
    water: 0,
    sleep: { done: false, quality: null },
    movement: { done: false, bucket: null },
    sun: { done: false, level: null },
  },
  aiChat: [
    { role: 'bot', text: '안녕! 낮엔 내가 도와줄게.\n오늘 뭐 도와줄까?' },
  ],
  chatDiary: [],
  diaries: SEED_DIARIES,
  selectedDay: 26,
  points: 240,
  streak: 12,
  level: 3,
  unlockedItems: ['🧣 스카프', '👕 줄무늬'],
  equippedItem: '👕 줄무늬',
};

type Action =
  | { type: 'character/set'; patch: Partial<State['character']> }
  | { type: 'daily/toggle-food'; pick: string }
  | { type: 'daily/water-set'; value: number }
  | { type: 'daily/sleep'; quality: string }
  | { type: 'daily/movement'; bucket: string }
  | { type: 'daily/sun'; level: string }
  | { type: 'ai-chat/append'; msg: ChatMsg }
  | { type: 'chat-diary/append'; msg: ChatMsg }
  | { type: 'chat-diary/reset' }
  | { type: 'diary/save'; entry: DiaryEntry }
  | { type: 'ui/select-day'; day: number }
  | { type: 'points/add'; delta: number }
  | { type: 'streak/inc' }
  | { type: 'item/equip'; item: string }
  | { type: 'item/unlock'; item: string }
  | { type: 'state/replace'; state: State };

function reducer(state: State, action: Action): State {
  switch (action.type) {
    case 'character/set':
      return { ...state, character: { ...state.character, ...action.patch } };
    case 'daily/toggle-food': {
      const has = state.daily.food.picks.includes(action.pick);
      const picks = has
        ? state.daily.food.picks.filter((p) => p !== action.pick)
        : [...state.daily.food.picks, action.pick];
      return {
        ...state,
        daily: {
          ...state.daily,
          food: { done: picks.length > 0, picks },
        },
      };
    }
    case 'daily/water-set':
      return {
        ...state,
        daily: { ...state.daily, water: Math.max(0, Math.min(8, action.value)) },
      };
    case 'daily/sleep':
      return {
        ...state,
        daily: {
          ...state.daily,
          sleep: { done: true, quality: action.quality },
        },
      };
    case 'daily/movement':
      return {
        ...state,
        daily: {
          ...state.daily,
          movement: { done: true, bucket: action.bucket },
        },
      };
    case 'daily/sun':
      return {
        ...state,
        daily: { ...state.daily, sun: { done: true, level: action.level } },
      };
    case 'ai-chat/append':
      return { ...state, aiChat: [...state.aiChat, action.msg] };
    case 'chat-diary/append':
      return { ...state, chatDiary: [...state.chatDiary, action.msg] };
    case 'chat-diary/reset':
      return { ...state, chatDiary: [] };
    case 'diary/save':
      return {
        ...state,
        diaries: [...state.diaries.filter((d) => d.day !== action.entry.day), action.entry],
        selectedDay: action.entry.day,
      };
    case 'ui/select-day':
      return { ...state, selectedDay: action.day };
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

const StoreContext = createContext<{
  state: State;
  dispatch: React.Dispatch<Action>;
}>({ state: DEFAULT_STATE, dispatch: () => undefined });

export const StoreProvider = ({ children }: { children: ReactNode }) => {
  const [state, dispatch] = useReducer(reducer, DEFAULT_STATE, (init) => {
    try {
      const raw = localStorage.getItem(LS_KEY);
      if (raw) return { ...init, ...(JSON.parse(raw) as State) };
    } catch {
      // ignore parse errors
    }
    return init;
  });

  useEffect(() => {
    try {
      localStorage.setItem(LS_KEY, JSON.stringify(state));
    } catch {
      // ignore quota
    }
  }, [state]);

  return (
    <StoreContext.Provider value={{ state, dispatch }}>
      {children}
    </StoreContext.Provider>
  );
};

export const useStore = () => useContext(StoreContext);

// ── 봇 응답 시뮬레이션 helpers ─────────────────────────────────────────────

const AI_CHAT_REPLIES: { keywords: string[]; replies: string[] }[] = [
  {
    keywords: ['점심', '먹', '입맛', '배고'],
    replies: [
      '속이 편한 게 좋겠다.\n죽 한 그릇 어때? 따뜻한 우동도 좋고.',
      '오늘 같은 날엔 김밥+계란국 조합도 좋아.\n어떤 게 끌려?',
    ],
  },
  {
    keywords: ['잠', '졸려', '피곤', '수면'],
    replies: [
      '오늘 너무 무리한 거 아니야?\n10분만 눈 감고 천천히 숨 쉬어볼래?',
      '잠이 안 올 땐 따뜻한 물 한 잔이 도움돼.\n자기 전 화면도 잠깐 멀리해보자.',
    ],
  },
  {
    keywords: ['외로', '심심', '혼자'],
    replies: [
      '나 여기 있어 :)\n오늘 가장 좋았던 순간이 뭐였어?',
      '집이 너무 조용할 땐 작은 백색소음도 좋아.\n뭐가 듣고 싶어?',
    ],
  },
  {
    keywords: ['루틴', '추천', '뭐 할'],
    replies: [
      '딱 3분 호흡 알람 어때?\n회의 끝나고 강제로 쉬는 시간을 만들어보자.',
      '저녁에 10분 산책 추천 — 햇볕보다 더 잘 와닿을 거야.',
    ],
  },
];

const FALLBACK_AI_REPLIES = [
  '음… 그렇구나. 그래서 어떤 기분이야?',
  '천천히 말해줘. 내가 듣고 있어.',
  '오늘 점심 뭐 먹었어?\n이건 회고에 미리 적어둘게 ✎',
  '그 얘기, 밤 회고 시간에 한 번 더 꺼내볼까?',
];

export const simulateAiReply = (userText: string): ChatMsg => {
  const lower = userText.toLowerCase();
  for (const group of AI_CHAT_REPLIES) {
    if (group.keywords.some((k) => lower.includes(k))) {
      const text = group.replies[Math.floor(Math.random() * group.replies.length)];
      return { role: 'bot', text };
    }
  }
  const text =
    FALLBACK_AI_REPLIES[Math.floor(Math.random() * FALLBACK_AI_REPLIES.length)];
  return { role: 'bot', text };
};

// ── ChatDiary 5턴 시퀀스 ─────────────────────────────────────────────────

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

export const todayDayNum = () => today.getDate();

// ── 달력·통계 집계 (on-device diaries에서 파생) ────────────────────────────
export type Period = '주' | '월' | '전체';
export const TODAY_DAY = 27; // 프로토타입 기준일 (5월 27일)

export const MOODS_ALL: Mood[] = ['😌', '😊', '😣', '😢', '😡'];
export const MOOD_LABEL: Record<Mood, string> = {
  '😌': '평온',
  '😊': '기쁨',
  '😣': '피곤',
  '😢': '슬픔',
  '😡': '짜증',
};
export const MOOD_BAR: Record<Mood, string> = {
  '😌': '#ead0a6',
  '😊': '#c9a266',
  '😣': '#d8a777',
  '😢': '#fff',
  '😡': '#fff5e1',
};
export const WEEKDAY_KR = ['일', '월', '화', '수', '목', '금', '토'];
// 5월 1일 2026 = 금요일 → 요일 인덱스(일=0..토=6)
export const weekdayOf = (day: number) => (4 + day) % 7;

export const entryForDay = (diaries: DiaryEntry[], day: number | null) =>
  day == null ? undefined : diaries.find((d) => d.day === day);

export const latestEntry = (diaries: DiaryEntry[]) =>
  diaries.length ? [...diaries].sort((a, b) => b.day - a.day)[0] : undefined;

// 달력 셀용: day → 대표 감정 이모지
export const moodByDay = (diaries: DiaryEntry[]): Record<number, Mood> => {
  const m: Record<number, Mood> = {};
  diaries.forEach((d) => {
    if (d.moods[0]) m[d.day] = d.moods[0];
  });
  return m;
};

// '전체'에서만 더해지는 이전 달(4월) 누적 baseline — 월/전체가 구분되도록
const HISTORY = {
  count: 22,
  writeDays: 22,
  weekday: [2, 4, 5, 3, 4, 3, 1],
  mood: { '😌': 9, '😊': 6, '😣': 4, '😢': 2, '😡': 1 } as Record<Mood, number>,
  life: { food: 19, water: 15, sleep: 12, movement: 9, sun: 11 },
};

export type StatsResult = {
  count: number;
  writeDays: number;
  target: number;
  weekday: number[];
  moodPct: { mood: Mood; label: string; pct: number; color: string }[];
  life: { food: number; water: number; sleep: number; movement: number; sun: number };
};

export const statsFor = (diaries: DiaryEntry[], period: Period): StatsResult => {
  const filtered =
    period === '주'
      ? diaries.filter((d) => d.day > TODAY_DAY - 7 && d.day <= TODAY_DAY)
      : diaries;

  const weekday = [0, 0, 0, 0, 0, 0, 0];
  const mood: Record<Mood, number> = { '😌': 0, '😊': 0, '😣': 0, '😢': 0, '😡': 0 };
  const life = { food: 0, water: 0, sleep: 0, movement: 0, sun: 0 };
  filtered.forEach((d) => {
    weekday[weekdayOf(d.day)]++;
    if (d.moods[0]) mood[d.moods[0]]++;
    (['food', 'water', 'sleep', 'movement', 'sun'] as DailyKey[]).forEach((k) => {
      if (d.check[k]) life[k]++;
    });
  });
  let count = filtered.length;
  let writeDays = new Set(filtered.map((d) => d.day)).size;

  if (period === '전체') {
    count += HISTORY.count;
    writeDays += HISTORY.writeDays;
    HISTORY.weekday.forEach((v, i) => (weekday[i] += v));
    MOODS_ALL.forEach((m) => (mood[m] += HISTORY.mood[m]));
    (Object.keys(life) as (keyof typeof life)[]).forEach((k) => (life[k] += HISTORY.life[k]));
  }

  const totalMood = MOODS_ALL.reduce((a, m) => a + mood[m], 0) || 1;
  const moodPct = MOODS_ALL.map((m) => ({
    mood: m,
    label: MOOD_LABEL[m],
    pct: Math.round((mood[m] / totalMood) * 100),
    color: MOOD_BAR[m],
  })).sort((a, b) => b.pct - a.pct);

  const target = period === '주' ? 7 : period === '월' ? 31 : writeDays;
  return { count, writeDays, target, weekday, moodPct, life };
};
