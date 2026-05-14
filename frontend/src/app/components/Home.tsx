import { PenLine, Calendar, Sparkles, TrendingUp, Heart, Gift, ChevronRight, Check } from 'lucide-react';
import { useState, useEffect } from 'react';
import { diaryApi, emotionApi } from '../utils/api';
import { getProgress, REWARDS } from '../utils/rewardSystem';
import { EumiCharacter } from './EumiCharacter';
import { getUserNickname } from '../utils/userProfile';

interface HomeProps {
  onStartDiary: () => void;
  onNavigate: (page: string) => void;
}

export function Home({ onStartDiary, onNavigate }: HomeProps) {
  const [todayDiaryExists, setTodayDiaryExists] = useState(false);
  const [recentSatisfaction, setRecentSatisfaction] = useState<number>(0);
  const [weekStreak, setWeekStreak] = useState(0);
  const [topEmotion, setTopEmotion] = useState<string>('');
  const [progress, setProgress] = useState(getProgress());
  const userNickname = getUserNickname();

  const today = new Date();
  const dateStr = today.toLocaleDateString('ko-KR', {
    month: 'long',
    day: 'numeric',
    weekday: 'long',
  });
  const timeStr = today.toLocaleTimeString('ko-KR', {
    hour: '2-digit',
    minute: '2-digit',
  });

  useEffect(() => {
    loadDashboardData();
    setProgress(getProgress());
  }, []);

  const loadDashboardData = async () => {
    try {
      const year = today.getFullYear();
      const month = today.getMonth() + 1;
      const response = await diaryApi.getList(year, month);
      const diaries = response.items; // DiaryListResponse에서 items 추출
      
      // 오늘 일기 확인
      const todayStr = today.toISOString().split('T')[0];
      const todayDiary = diaries.find(d => d.date === todayStr);
      setTodayDiaryExists(!!todayDiary);

      // 최근 만족도
      if (diaries.length > 0) {
        setRecentSatisfaction(diaries[diaries.length - 1].satisfaction);
      }

      // 연속 기록일
      setWeekStreak(diaries.length);

      // 감정 통계
      const stats = await emotionApi.getStats('week');
      if (stats.emotions.length > 0) {
        setTopEmotion(stats.emotions[0].name);
      }
    } catch (error) {
      console.error('Failed to load dashboard data:', error);
    }
  };

  const nextReward = REWARDS.find(r => r.requiredStreak > progress.currentStreak);

  return (
    <div className="flex flex-col h-full max-w-lg mx-auto">
      <div className="flex-1 overflow-y-auto smooth-scrollbar px-5 py-6 space-y-5 animate-fade-in">
        {/* 헤더 - 이음이 소개 (바텐더 스타일) */}
        <div className="card-elevated p-6">
          <div className="flex items-center gap-4">
            <div className="relative">
              <div className="w-16 h-16 bg-gradient-accent rounded-[1.4rem] flex items-center justify-center shadow-[0_4px_16px_rgba(164,124,75,0.3)]">
                <span className="text-3xl">🐱</span>
              </div>
              {!todayDiaryExists && (
                <div className="absolute -bottom-1 -right-1 w-4 h-4 bg-[#A47C4B] rounded-full border-2 border-white animate-pulse shadow-md"></div>
              )}
            </div>
            <div className="flex-1">
              <p className="text-xs text-[#8B7A6A] font-sans-system tracking-widest uppercase mb-1">
                Welcome Back, {userNickname}
              </p>
              <h1 className="text-xl font-black text-[#2C2419] tracking-tight font-title italic">
                Tamanya
              </h1>
            </div>
          </div>
          <div className="mt-4 pt-4 border-t-2 border-[#E5DDD3]/50 flex items-center justify-between">
            <p className="text-xs text-[#5A4A3A] font-diary">{dateStr}</p>
            <div className="flex items-center gap-3">
              <div className="flex items-center gap-1.5 px-3 py-1.5 bg-gradient-accent rounded-full">
                <span className="text-xs font-black text-white">Lv.{progress.level}</span>
              </div>
              <div className="w-px h-4 bg-[#E5DDD3]"></div>
              <div className="flex items-center gap-1.5">
                <span className="text-xs font-black text-[#5A4A3A]">🔥</span>
                <span className="text-xs font-black text-[#5A4A3A]">{weekStreak}</span>
              </div>
            </div>
          </div>
        </div>

        {/* 오늘의 일기 카드 (바텐더 스타일 강화) */}
        {!todayDiaryExists ? (
          <button
            onClick={onStartDiary}
            className="w-full card-butler p-8 hover:shadow-[0_12px_40px_rgba(0,0,0,0.4)] transition-all active:scale-[0.98] group"
          >
            <div className="flex items-center justify-between">
              <div className="text-left flex-1">
                <div className="inline-block mb-4">
                  <div className="w-14 h-14 bg-white/10 rounded-[1.2rem] flex items-center justify-center backdrop-blur-sm">
                    <span className="text-3xl">✍️</span>
                  </div>
                </div>
                <h2 className="font-black text-2xl text-[#F7F3EE] mb-2 tracking-tight font-title italic leading-tight">
                  오늘 하루 어땠어?<br/>잠깐 같이 돌아볼까.
                </h2>
                <p className="text-sm text-[#E5DDD3] font-diary">
                  이음이가 기다리고 있어요
                </p>
              </div>
              <ChevronRight size={28} className="text-[#A47C4B] group-hover:translate-x-1 transition-transform" />
            </div>
          </button>
        ) : (
          <div className="card-elevated p-6">
            <div className="flex items-center gap-4">
              <div className="w-12 h-12 bg-gradient-accent rounded-full flex items-center justify-center shadow-[0_4px_16px_rgba(164,124,75,0.3)]">
                <Check className="w-6 h-6 text-white" />
              </div>
              <div className="flex-1">
                <h3 className="font-bold text-[#2C2419] mb-1">오늘의 기록 완료</h3>
                <p className="text-sm text-[#8B7A6A] font-diary">잘 담아뒀어. 네 기기 안에서만. 🐱</p>
              </div>
            </div>
          </div>
        )}

        {/* 연속 기록 & 다음 보상 (바텐더 스타일) */}
        <div className="bg-gradient-to-br from-[#A47C4B]/10 to-[#C4966D]/10 rounded-[2rem] p-6 border-2 border-[#E5DDD3]">
          <div className="flex items-center justify-between mb-4">
            <div>
              <p className="text-xs text-[#8B7A6A] mb-2 uppercase tracking-widest font-sans-system">
                {progress.currentStreak}일째 함께 키우는 중 ✦
              </p>
              <p className="text-4xl font-black text-[#2C2419] font-title">
                {progress.currentStreak}
                <span className="text-xl text-[#8B7A6A] ml-1">days</span>
              </p>
            </div>
            <div className="text-5xl opacity-90">🔥</div>
          </div>
          
          {nextReward && (
            <div className="pt-4 border-t-2 border-[#E5DDD3]/50">
              <div className="flex items-center justify-between mb-3">
                <p className="text-xs text-[#8B7A6A] uppercase tracking-wide font-sans-system">
                  Next Reward
                </p>
                <p className="text-sm font-bold text-[#A47C4B]">
                  +{nextReward.requiredStreak - progress.currentStreak}일
                </p>
              </div>
              <div className="bg-[#E5DDD3] rounded-full h-2.5 overflow-hidden mb-3">
                <div
                  className="bg-gradient-accent h-full rounded-full transition-all duration-700"
                  style={{ width: `${(progress.currentStreak / nextReward.requiredStreak) * 100}%` }}
                />
              </div>
              <div className="flex items-center gap-2.5">
                <span className="text-2xl">{nextReward.emoji}</span>
                <span className="text-sm font-semibold text-[#2C2419]">{nextReward.name}</span>
              </div>
            </div>
          )}
        </div>

        {/* 통계 카드 그리드 */}
        <div className="grid grid-cols-2 gap-3">
          {/* 총 기록일 */}
          <div className="card-elevated p-5">
            <div className="flex items-center gap-2 mb-3">
              <div className="w-9 h-9 bg-[#A47C4B]/10 rounded-xl flex items-center justify-center">
                <span className="text-xl">📝</span>
              </div>
              <span className="text-xs text-[#8B7A6A] uppercase tracking-wide font-sans-system">Total</span>
            </div>
            <p className="text-3xl font-black text-[#2C2419] font-title">{progress.totalDiaries}</p>
            <p className="text-xs text-[#8B7A6A] mt-1.5">일 기록</p>
          </div>

          {/* 포인트 */}
          <div className="card-elevated p-5">
            <div className="flex items-center gap-2 mb-3">
              <div className="w-9 h-9 bg-[#D4A574]/10 rounded-xl flex items-center justify-center">
                <span className="text-xl">⭐</span>
              </div>
              <span className="text-xs text-[#8B7A6A] uppercase tracking-wide font-sans-system">Points</span>
            </div>
            <p className="text-3xl font-black text-gradient-gold font-title">{progress.points}</p>
            <p className="text-xs text-[#8B7A6A] mt-1.5">포인트</p>
          </div>
        </div>

        {/* 빠른 메뉴 */}
        <div className="space-y-3">
          <h3 className="font-bold text-[#2C2419] px-2 text-xs uppercase tracking-widest font-sans-system">
            Quick Menu
          </h3>
          
          <button
            onClick={() => onNavigate('inventory')}
            className="w-full card-elevated p-5 hover:shadow-[0_8px_30px_rgba(44,36,25,0.1)] transition-all active:scale-[0.98] text-left group"
          >
            <div className="flex items-center gap-4">
              <div className="w-12 h-12 bg-gradient-to-br from-[#7B4B5A] to-[#9B6B7A] rounded-[1.2rem] flex items-center justify-center shadow-[0_4px_16px_rgba(123,75,90,0.3)] flex-shrink-0 group-hover:scale-110 transition-transform">
                <Gift className="w-6 h-6 text-white" strokeWidth={2.5} />
              </div>
              <div className="flex-1">
                <h4 className="font-bold text-[#2C2419] mb-1">인벤토리</h4>
                <p className="text-sm text-[#8B7A6A]">보상과 아이템 확인</p>
              </div>
              {progress.inventory.length > 0 && (
                <div className="w-7 h-7 bg-[#A47C4B] text-white rounded-full flex items-center justify-center text-xs font-black shadow-[0_2px_8px_rgba(164,124,75,0.4)]">
                  {progress.inventory.length}
                </div>
              )}
            </div>
          </button>

          <button
            onClick={() => onNavigate('calendar')}
            className="w-full card-elevated p-5 hover:shadow-[0_8px_30px_rgba(44,36,25,0.1)] transition-all active:scale-[0.98] text-left group"
          >
            <div className="flex items-center gap-4">
              <div className="w-12 h-12 bg-gradient-to-br from-[#4A5C4B] to-[#6A7C6B] rounded-[1.2rem] flex items-center justify-center shadow-[0_4px_16px_rgba(74,92,75,0.3)] flex-shrink-0 group-hover:scale-110 transition-transform">
                <Calendar className="w-6 h-6 text-white" strokeWidth={2.5} />
              </div>
              <div>
                <h4 className="font-bold text-[#2C2419] mb-1">캘린더</h4>
                <p className="text-sm text-[#8B7A6A]">과거 기록 확인</p>
              </div>
            </div>
          </button>

          <button
            onClick={() => onNavigate('insights')}
            className="w-full card-elevated p-5 hover:shadow-[0_8px_30px_rgba(44,36,25,0.1)] transition-all active:scale-[0.98] text-left group"
          >
            <div className="flex items-center gap-4">
              <div className="w-12 h-12 bg-gradient-accent rounded-[1.2rem] flex items-center justify-center shadow-[0_4px_16px_rgba(164,124,75,0.3)] flex-shrink-0 group-hover:scale-110 transition-transform">
                <Sparkles className="w-6 h-6 text-white" strokeWidth={2.5} />
              </div>
              <div>
                <h4 className="font-bold text-[#2C2419] mb-1">인사이트</h4>
                <p className="text-sm text-[#8B7A6A]">AI 감정 분석</p>
              </div>
            </div>
          </button>
        </div>

        {/* 이음이 팁 (바텐더 스타일) */}
        <div className="card-butler p-6">
          <div className="flex gap-4">
            <div className="w-10 h-10 bg-white/10 rounded-xl flex items-center justify-center backdrop-blur-sm flex-shrink-0">
              <span className="text-2xl">💡</span>
            </div>
            <div>
              <h3 className="font-bold text-[#F7F3EE] mb-2 font-title italic">이음이의 한마디</h3>
              <p className="text-sm text-[#E5DDD3] leading-relaxed font-diary">
                매일 작은 루틴 하나씩. 이음이가 매일 같이 있어줄게. 오늘도 수고했어.
              </p>
            </div>
          </div>
        </div>

        {/* 개발자 모드: 온보딩 재실행 버튼 */}
        <button
          onClick={() => {
            localStorage.removeItem('hasVisited');
            window.location.reload();
          }}
          className="w-full bg-white/60 border-2 border-[#E5DDD3] rounded-[1.5rem] p-3 text-xs text-[#8B7A6A] hover:bg-white hover:border-[#D4C4B4] transition-all font-sans-system"
        >
          🔄 온보딩 다시 보기
        </button>
      </div>
    </div>
  );
}