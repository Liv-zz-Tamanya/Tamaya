import { useState, useEffect } from 'react';
import { Sparkles } from 'lucide-react';
import { getProgress, REWARDS, useItem, UserProgress } from '../utils/rewardSystem';
import { EumiCharacter } from './EumiCharacter';

// BE GET /game/state placeholder mock (DEC-022.C — Phase 1 BE 연동 예정)
interface GameState {
  level: number;
  currentStreak: number;
  points: number;
  affection: number; // 0~100 호감도 게이지
  inventory: string[];
}

function getGameStateMock(): GameState {
  const p = getProgress();
  const affection = Math.min(100, Math.round((p.currentStreak / 21) * 100));
  return {
    level: p.level,
    currentStreak: p.currentStreak,
    points: p.points,
    affection,
    inventory: p.inventory,
  };
}

export function InventoryPage() {
  const [progress, setProgress] = useState<UserProgress>(getProgress());
  const [gameState, setGameState] = useState<GameState>(getGameStateMock());
  const [selectedItem, setSelectedItem] = useState<string | null>(null);
  const [isUsing, setIsUsing] = useState(false);

  useEffect(() => {
    setProgress(getProgress());
    setGameState(getGameStateMock());
  }, []);

  const inventoryItems = REWARDS.filter(reward =>
    progress.inventory.includes(reward.id)
  );

  const handleUseItem = (itemId: string) => {
    setSelectedItem(itemId);
    setIsUsing(true);
    setTimeout(() => {
      const updatedProgress = useItem(itemId);
      setProgress(updatedProgress);
      setGameState(getGameStateMock());
      setIsUsing(false);
      setSelectedItem(null);
    }, 2000);
  };

  return (
    <div className="flex flex-col h-full max-w-lg mx-auto bg-[#FAF8F5]">
      {/* 헤더 */}
      <div className="bg-white/80 backdrop-blur-sm border-b border-[rgba(0,0,0,0.06)] px-4 py-4">
        <div className="flex items-center gap-3 mb-4">
          <div className="w-10 h-10 bg-gradient-to-br from-[#A47C4B] to-[#C4966D] rounded-full flex items-center justify-center shadow-sm">
            <span className="text-xl">🐱</span>
          </div>
          <div>
            <h1 className="font-semibold text-[#4A4A4A]">키우기</h1>
            {/* CMO #17 호감도 게이지 레이블 */}
            <p className="text-xs text-[#8A8A8A]">이음이와의 시간</p>
          </div>
        </div>

        {/* 레벨 + 포인트 */}
        <div className="flex gap-3 mb-3">
          <div className="flex-1 bg-gradient-to-r from-[#A47C4B]/20 to-[#C4966D]/20 rounded-[1rem] px-4 py-2 flex items-center justify-between">
            <span className="text-sm text-[#4A4A4A]">레벨</span>
            <span className="font-bold text-lg text-[#A47C4B]">Lv.{gameState.level}</span>
          </div>
          <div className="flex-1 bg-gradient-to-r from-[#4A5C4B]/20 to-[#6A7C6B]/20 rounded-[1rem] px-4 py-2 flex items-center justify-between">
            <span className="text-sm text-[#4A4A4A]">포인트</span>
            <span className="font-bold text-lg text-[#4A5C4B]">{gameState.points}</span>
          </div>
        </div>

        {/* 호감도 게이지 (CMO #17) */}
        <div className="bg-[#F7F3EE] rounded-[1rem] px-4 py-3">
          <div className="flex items-center justify-between mb-2">
            <span className="text-xs text-[#8B7A6A] font-semibold">이음이와의 시간</span>
            <span className="text-xs font-black text-[#A47C4B]">{gameState.affection}%</span>
          </div>
          <div className="bg-[#E5DDD3] rounded-full h-2.5 overflow-hidden">
            <div
              className="bg-gradient-to-r from-[#A47C4B] to-[#C4966D] h-full rounded-full transition-all duration-700"
              style={{ width: `${gameState.affection}%` }}
            />
          </div>
          <p className="text-xs text-[#8B7A6A] mt-1.5 font-diary">
            {gameState.currentStreak}일째 함께 키우는 중 ✦
          </p>
        </div>
      </div>

      {/* 이음이 상태 애니메이션 (아이템 사용 시) */}
      {isUsing && (
        <div className="bg-gradient-to-r from-[#A47C4B]/20 to-[#C4966D]/20 px-6 py-8 text-center">
          <EumiCharacter size="xl" mood="excited" />
          {/* CMO #16 레벨업 알림 */}
          <p className="mt-4 font-semibold text-[#4A4A4A]">
            이음이가 더 가까워졌어! 오늘도 수고했어.
          </p>
        </div>
      )}

      {/* 보상 로드맵 카드 (Day 3·5·7·10·14·21) */}
      <div className="px-4 pt-4 pb-2">
        <h2 className="text-xs text-[#8B7A6A] uppercase tracking-widest font-sans-system mb-3">
          보상 로드맵
        </h2>
        <div className="grid grid-cols-3 gap-2">
          {REWARDS.map((reward) => {
            const unlocked = progress.inventory.includes(reward.id);
            const reachable = gameState.currentStreak >= reward.requiredStreak;
            return (
              <div
                key={reward.id}
                className={`rounded-[1.2rem] p-3 text-center transition-all border-2 ${
                  unlocked
                    ? 'bg-gradient-to-br from-[#A47C4B]/20 to-[#C4966D]/20 border-[#A47C4B]/40'
                    : reachable
                    ? 'bg-white border-[#A47C4B]/60 shadow-sm'
                    : 'bg-[#F7F3EE] border-[#E5DDD3] opacity-60'
                }`}
              >
                <div className={`text-2xl mb-1 ${!reachable && !unlocked ? 'grayscale opacity-50' : ''}`}>
                  {reward.emoji}
                </div>
                <p className="text-xs font-semibold text-[#4A4A4A] leading-tight mb-0.5">
                  {reward.name}
                </p>
                <p className="text-[10px] text-[#8B7A6A]">
                  {unlocked ? '✅ 획득' : `Day ${reward.requiredStreak}`}
                </p>
              </div>
            );
          })}
        </div>
      </div>

      {/* 인벤토리 아이템 */}
      <div className="flex-1 overflow-y-auto px-4 py-4 space-y-4">
        {inventoryItems.length > 0 ? (
          <>
            <h2 className="text-xs text-[#8B7A6A] uppercase tracking-widest font-sans-system">
              내 아이템
            </h2>
            <div className="grid grid-cols-2 gap-3">
              {inventoryItems.map((item) => {
                const count = progress.inventory.filter(id => id === item.id).length;
                return (
                  <button
                    key={item.id}
                    onClick={() => handleUseItem(item.id)}
                    disabled={isUsing}
                    className="bg-white/80 backdrop-blur-sm rounded-[1.5rem] p-5 shadow-sm hover:shadow-md transition-all active:scale-95 disabled:opacity-50 text-left"
                  >
                    <div className="text-4xl mb-2">{item.emoji}</div>
                    <h3 className="font-semibold text-sm text-[#4A4A4A] mb-1">{item.name}</h3>
                    <p className="text-xs text-[#8A8A8A] mb-2">{item.description}</p>
                    {count > 1 && (
                      <div className="inline-block px-2 py-1 bg-[#A47C4B]/20 rounded-full text-xs font-semibold text-[#A47C4B]">
                        x{count}
                      </div>
                    )}
                  </button>
                );
              })}
            </div>

            {/* 이음이 tip */}
            <div className="bg-[#FFF5E6]/60 rounded-[1.5rem] p-5 shadow-sm border border-[#E5DDD3]">
              <div className="flex gap-3">
                <EumiCharacter size="sm" mood="happy" />
                <div>
                  <p className="text-sm text-[#6A6A6A] leading-relaxed">
                    <span className="font-semibold text-[#4A4A4A]">이음이 tip:</span>{' '}
                    아이템을 터치하면 이음이와 함께 사용할 수 있어요. 사용하면 보너스 포인트도 받아!
                  </p>
                </div>
              </div>
            </div>
          </>
        ) : (
          <div className="flex flex-col items-center justify-center py-8 text-center">
            <EumiCharacter size="lg" mood="neutral" />
            <p className="font-medium text-[#4A4A4A] mb-2 mt-4">아직 아이템이 없어</p>
            <p className="text-sm text-[#8A8A8A] px-8 font-diary">
              꾸준히 일기를 작성하면<br />
              이음이를 위한 선물을 받을 수 있어요!
            </p>
            {/* CMO #18 보상 잠금 해제 메시지 */}
            <div className="mt-4 bg-white/80 rounded-[1.5rem] p-4 shadow-sm max-w-xs">
              <div className="flex items-center gap-2">
                <Sparkles className="w-4 h-4 text-[#A47C4B]" />
                <p className="text-xs text-[#6A6A6A] font-diary">
                  {gameState.currentStreak > 0
                    ? `${gameState.currentStreak}일을 함께했더니, 새로운 이음이 표정이 생겼어`
                    : '3일을 함께하면 첫 선물을 드려요!'}
                </p>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
