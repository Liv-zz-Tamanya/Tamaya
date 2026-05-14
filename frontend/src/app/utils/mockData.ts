// Mock 데이터
import { DiaryEntry, EmotionStats, DailyInsight, WeeklyReport } from './api';

export const mockDiaryList: DiaryEntry[] = [
  {
    id: 'diary-1',
    date: '2026-02-05',
    content: '오늘은 새로운 프로젝트를 시작했다. 설레는 마음과 동시에 약간의 걱정도 들었지만, 팀원들과 함께라면 잘 해낼 수 있을 것 같다.',
    emotion: '설렘', // 단일 감정으로 변경
    satisfaction: 75,
    createdAt: '2026-02-05T22:30:00Z',
    chatLog: [
      {
        id: 'msg-1',
        role: 'assistant',
        content: '안녕하세요! 오늘 하루는 어떠셨나요?',
        timestamp: '2026-02-05T22:25:00Z',
      },
      {
        id: 'msg-2',
        role: 'user',
        content: '새로운 프로젝트를 시작했어요',
        timestamp: '2026-02-05T22:26:00Z',
      },
    ],
  },
  {
    id: 'diary-2',
    date: '2026-02-06',
    content: '친구들과 오랜만에 만나서 맛있는 음식을 먹었다. 웃고 떠들면서 스트레스가 많이 풀렸다.',
    emotion: '기쁨', // 단일 감정으로 변경
    satisfaction: 90,
    createdAt: '2026-02-06T23:00:00Z',
  },
  {
    id: 'diary-3',
    date: '2026-02-07',
    content: '업무가 많아서 조금 힘들었지만, 하나씩 해결해 나가는 과정에서 보람을 느꼈다.',
    emotion: '보람', // 단일 감정으로 변경
    satisfaction: 70,
    createdAt: '2026-02-07T21:45:00Z',
  },
  {
    id: 'diary-4',
    date: '2026-02-08',
    content: '휴일을 맞아 집에서 푹 쉬었다. 좋아하는 영화를 보고 책도 읽으면서 여유로운 시간을 보냈다.',
    emotion: '편안함', // 단일 감정으로 변경
    satisfaction: 85,
    createdAt: '2026-02-08T20:00:00Z',
  },
];

export const mockEmotionStats: EmotionStats = {
  period: 'week',
  emotions: [
    { name: '기쁨', count: 8, emoji: '😊' },
    { name: '편안함', count: 6, emoji: '😌' },
    { name: '감사', count: 5, emoji: '🙏' },
    { name: '보람', count: 4, emoji: '✨' },
    { name: '피곤함', count: 3, emoji: '😴' },
    { name: '설렘', count: 2, emoji: '💖' },
  ],
  satisfactionAvg: 80,
  totalDays: 7,
};

export const mockDailyInsight: DailyInsight = {
  date: '2026-02-09',
  insight: '오늘은 긍정적인 감정이 많았던 하루였네요. 특히 대인관계에서 만족감을 느끼셨던 것 같아요.',
  tip: '이러한 긍정적인 에너지를 내일도 이어가보세요. 감사했던 순간들을 떠올려보는 것도 좋습니다.',
};

export const mockWeeklyReport: WeeklyReport = {
  startDate: '2026-02-03',
  endDate: '2026-02-09',
  summary: '이번 주는 전반적으로 안정적인 감정 상태를 유지하셨습니다. 기쁨과 편안함이 가장 자주 나타났으며, 평균 만족도는 80점으로 양호한 편입니다.',
  topEmotions: ['기쁨', '편안함', '감사'],
  avgSatisfaction: 80,
  tips: [
    '규칙적인 수면 패턴을 유지하세요',
    '주 2-3회 가벼운 운동을 추천합니다',
    '가까운 사람들과의 교류를 이어가세요',
  ],
};

// 감정 리스트 (15개 기본 감정)
export const EMOTIONS = [
  { name: '기쁨', emoji: '😊' },
  { name: '행복', emoji: '😄' },
  { name: '설렘', emoji: '💖' },
  { name: '편안함', emoji: '😌' },
  { name: '감사', emoji: '🙏' },
  { name: '보람', emoji: '✨' },
  { name: '슬픔', emoji: '😢' },
  { name: '외로움', emoji: '😔' },
  { name: '불안', emoji: '😰' },
  { name: '화남', emoji: '😠' },
  { name: '피곤함', emoji: '😴' },
  { name: '스트레스', emoji: '😫' },
  { name: '지루함', emoji: '😑' },
  { name: '긴장', emoji: '😬' },
  { name: '집중', emoji: '🎯' },
];

// 대화형 가이드 질문
export const GUIDE_QUESTIONS = [
  '안녕하세요! 저는 이음이에요 🤗 오늘 하루는 어떠셨나요?',
  '오늘 가장 기억에 남는 일이 있나요?',
  '그 순간에 어떤 감정을 느끼셨어요?',
  '오늘의 컨디션은 어떠셨나요?',
  '오늘 하루를 한 문장으로 표현한다면 어떨까요?',
];