// 보상 시스템
export interface Reward {
  id: string;
  name: string;
  emoji: string;
  type: 'toy' | 'snack';
  description: string;
  requiredStreak: number;
}

export interface UserProgress {
  currentStreak: number;
  totalDiaries: number;
  points: number;
  level: number;
  inventory: string[]; // reward IDs
  lastRewardDate: string | null;
}

export const REWARDS: Reward[] = [
  {
    id: 'churu_1',
    name: '츄르 (참치맛)',
    emoji: '🍖',
    type: 'snack',
    description: '이음이가 좋아하는 츄르예요!',
    requiredStreak: 3
  },
  {
    id: 'toy_ball',
    name: '털실 공',
    emoji: '🧶',
    type: 'toy',
    description: '이음이가 가지고 놀 수 있어요',
    requiredStreak: 5
  },
  {
    id: 'churu_2',
    name: '츄르 (연어맛)',
    emoji: '🐟',
    type: 'snack',
    description: '프리미엄 연어 츄르!',
    requiredStreak: 7
  },
  {
    id: 'toy_mouse',
    name: '쥐 인형',
    emoji: '🐭',
    type: 'toy',
    description: '부드러운 쥐 인형이에요',
    requiredStreak: 10
  },
  {
    id: 'toy_feather',
    name: '깃털 장난감',
    emoji: '🪶',
    type: 'toy',
    description: '이음이가 점프하며 놀아요',
    requiredStreak: 14
  },
  {
    id: 'churu_premium',
    name: '프리미엄 츄르 세트',
    emoji: '✨',
    type: 'snack',
    description: '특별한 날을 위한 세트!',
    requiredStreak: 21
  }
];

// 로컬 스토리지 키
const PROGRESS_KEY = 'eumi_progress';

// 초기 진행도
const DEFAULT_PROGRESS: UserProgress = {
  currentStreak: 0,
  totalDiaries: 0,
  points: 0,
  level: 1,
  inventory: [],
  lastRewardDate: null
};

// 진행도 불러오기
export function getProgress(): UserProgress {
  try {
    const saved = localStorage.getItem(PROGRESS_KEY);
    if (saved) {
      return JSON.parse(saved);
    }
  } catch (error) {
    console.error('Failed to load progress:', error);
  }
  return { ...DEFAULT_PROGRESS };
}

// 진행도 저장
export function saveProgress(progress: UserProgress): void {
  try {
    localStorage.setItem(PROGRESS_KEY, JSON.stringify(progress));
  } catch (error) {
    console.error('Failed to save progress:', error);
  }
}

// 일기 작성 시 진행도 업데이트
export function updateProgressOnDiary(): UserProgress {
  const progress = getProgress();
  
  progress.currentStreak += 1;
  progress.totalDiaries += 1;
  progress.points += 10;
  
  // 레벨업 (10일마다)
  progress.level = Math.floor(progress.totalDiaries / 10) + 1;
  
  saveProgress(progress);
  return progress;
}

// 획득 가능한 보상 확인
export function getAvailableRewards(currentStreak: number): Reward[] {
  return REWARDS.filter(
    reward => reward.requiredStreak <= currentStreak
  );
}

// 새 보상 확인
export function getNewRewards(progress: UserProgress): Reward[] {
  const available = getAvailableRewards(progress.currentStreak);
  return available.filter(reward => !progress.inventory.includes(reward.id));
}

// 보상 수령
export function claimReward(rewardId: string): UserProgress {
  const progress = getProgress();
  
  if (!progress.inventory.includes(rewardId)) {
    progress.inventory.push(rewardId);
    progress.lastRewardDate = new Date().toISOString();
    saveProgress(progress);
  }
  
  return progress;
}

// 연속 기록 초기화 (일기 작성 안 한 경우)
export function resetStreak(): UserProgress {
  const progress = getProgress();
  progress.currentStreak = 0;
  saveProgress(progress);
  return progress;
}

// 아이템 사용
export function useItem(itemId: string): UserProgress {
  const progress = getProgress();
  const index = progress.inventory.indexOf(itemId);
  
  if (index > -1) {
    progress.inventory.splice(index, 1);
    progress.points += 5; // 사용 시 보너스 포인트
    saveProgress(progress);
  }
  
  return progress;
}
