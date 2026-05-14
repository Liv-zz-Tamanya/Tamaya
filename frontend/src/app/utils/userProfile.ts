// 사용자 프로필 관리 유틸리티

export interface UserProfile {
  nickname: string;
  preferredEmotions: string[];
  dailyGoal: string;
  createdAt: string;
}

// 사용자 프로필 저장
export function saveUserProfile(profile: Partial<UserProfile>): void {
  const existingProfile = getUserProfile();
  const updatedProfile = {
    ...existingProfile,
    ...profile,
    createdAt: existingProfile.createdAt || new Date().toISOString(),
  };
  localStorage.setItem('userProfile', JSON.stringify(updatedProfile));
}

// 사용자 프로필 가져오기
export function getUserProfile(): UserProfile {
  const stored = localStorage.getItem('userProfile');
  if (stored) {
    return JSON.parse(stored);
  }
  return {
    nickname: '',
    preferredEmotions: [],
    dailyGoal: '',
    createdAt: '',
  };
}

// 사용자 닉네임 가져오기
export function getUserNickname(): string {
  const profile = getUserProfile();
  return profile.nickname || '고객님';
}

// 선호 감정 가져오기
export function getPreferredEmotions(): string[] {
  const profile = getUserProfile();
  return profile.preferredEmotions || [];
}

// 일일 목표 가져오기
export function getDailyGoal(): string {
  const profile = getUserProfile();
  return profile.dailyGoal || '';
}

// 온보딩 완료 여부 확인
export function isOnboardingComplete(): boolean {
  return localStorage.getItem('hasVisited') === 'true';
}

// 사용자 프로필 초기화 (개발용)
export function resetUserProfile(): void {
  localStorage.removeItem('userProfile');
  localStorage.removeItem('hasVisited');
}

// 감정 레이블 매핑
export const emotionLabels: Record<string, string> = {
  happy: '기쁨',
  calm: '평온',
  love: '사랑',
  sad: '슬픔',
  angry: '화남',
  anxious: '불안',
};

// 감정 이모지 매핑
export const emotionEmojis: Record<string, string> = {
  happy: '😊',
  calm: '😌',
  love: '🥰',
  sad: '😢',
  angry: '😠',
  anxious: '😰',
};

// 선호 감정을 라벨로 변환
export function getPreferredEmotionLabels(): string[] {
  const emotions = getPreferredEmotions();
  return emotions.map(id => emotionLabels[id] || id);
}
