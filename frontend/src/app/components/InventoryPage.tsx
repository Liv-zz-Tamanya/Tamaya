import { useState, useEffect } from 'react';
import { Package, Sparkles } from 'lucide-react';
import { getProgress, REWARDS, useItem, saveProgress, UserProgress } from '../utils/rewardSystem';
import { EumiCharacter } from './EumiCharacter';

export function InventoryPage() {
  const [progress, setProgress] = useState<UserProgress>(getProgress());
  const [selectedItem, setSelectedItem] = useState<string | null>(null);
  const [isUsing, setIsUsing] = useState(false);

  useEffect(() => {
    setProgress(getProgress());
  }, []);

  const inventoryItems = REWARDS.filter(reward => 
    progress.inventory.includes(reward.id)
  );

  const handleUseItem = (itemId: string) => {
    setSelectedItem(itemId);
    setIsUsing(true);

    // 애니메이션 효과
    setTimeout(() => {
      const updatedProgress = useItem(itemId);
      setProgress(updatedProgress);
      setIsUsing(false);
      setSelectedItem(null);
    }, 2000);
  };

  return (
    <div className="flex flex-col h-full max-w-lg mx-auto bg-[#FAF8F5]">
      {/* 헤더 */}
      <div className="bg-white/80 backdrop-blur-sm border-b border-[rgba(0,0,0,0.06)] px-4 py-4">
        <div className="flex items-center gap-3 mb-4">
          <div className="w-10 h-10 bg-gradient-to-br from-[#FFB4B4] to-[#FFDEB4] rounded-full flex items-center justify-center shadow-sm">
            <Package className="w-5 h-5 text-[#4A4A4A]" />
          </div>
          <div>
            <h1 className="font-semibold text-[#4A4A4A]">인벤토리</h1>
            <p className="text-xs text-[#8A8A8A]">이음이와 함께 사용해요</p>
          </div>
        </div>

        {/* 포인트 */}
        <div className="flex gap-3">
          <div className="flex-1 bg-gradient-to-r from-[#FFB4B4]/20 to-[#FFDEB4]/20 rounded-[1rem] px-4 py-2 flex items-center justify-between">
            <span className="text-sm text-[#4A4A4A]">레벨</span>
            <span className="font-bold text-lg text-[#FFB4B4]">{progress.level}</span>
          </div>
          <div className="flex-1 bg-gradient-to-r from-[#B4D4FF]/20 to-[#D4B4FF]/20 rounded-[1rem] px-4 py-2 flex items-center justify-between">
            <span className="text-sm text-[#4A4A4A]">포인트</span>
            <span className="font-bold text-lg text-[#B4D4FF]">{progress.points}</span>
          </div>
        </div>
      </div>

      {/* 이음이 상태 */}
      {isUsing && (
        <div className="bg-gradient-to-r from-[#B4D4FF] to-[#D4B4FF] px-6 py-8 text-center">
          <EumiCharacter size="xl" mood="excited" />
          <p className="mt-4 font-semibold text-[#4A4A4A]">
            이음이가 기뻐해요! 😊
          </p>
        </div>
      )}

      {/* 인벤토리 아이템 */}
      <div className="flex-1 overflow-y-auto px-4 py-6 space-y-4">
        {inventoryItems.length > 0 ? (
          <>
            <div className="grid grid-cols-2 gap-3">
              {inventoryItems.map((item) => {
                const count = progress.inventory.filter(id => id === item.id).length;
                
                return (
                  <button
                    key={item.id}
                    onClick={() => handleUseItem(item.id)}
                    disabled={isUsing}
                    className="bg-white/80 backdrop-blur-sm rounded-[1.5rem] p-5 shadow-sm hover:shadow-md transition-all active:scale-95 disabled:opacity-50"
                  >
                    <div className="text-5xl mb-3">{item.emoji}</div>
                    <h3 className="font-semibold text-sm text-[#4A4A4A] mb-1">
                      {item.name}
                    </h3>
                    <p className="text-xs text-[#8A8A8A] mb-2">
                      {item.description}
                    </p>
                    {count > 1 && (
                      <div className="inline-block px-2 py-1 bg-[#FFB4B4]/20 rounded-full text-xs font-semibold text-[#FFB4B4]">
                        x{count}
                      </div>
                    )}
                  </button>
                );
              })}
            </div>

            {/* 안내 */}
            <div className="bg-[#FFDEB4]/20 rounded-[1.5rem] p-5 shadow-sm">
              <div className="flex gap-3">
                <EumiCharacter size="sm" mood="happy" />
                <div>
                  <p className="text-sm text-[#6A6A6A] leading-relaxed">
                    <span className="font-semibold text-[#4A4A4A]">이음이 tip:</span> 아이템을 터치하면 이음이와 함께 사용할 수 있어요! 사용하면 보너스 포인트도 받을 수 있답니다.
                  </p>
                </div>
              </div>
            </div>
          </>
        ) : (
          <div className="flex flex-col items-center justify-center h-full text-center">
            <div className="w-24 h-24 bg-gradient-to-br from-[#FFB4B4]/20 to-[#FFDEB4]/20 rounded-full flex items-center justify-center mb-4">
              <Package className="w-12 h-12 text-[#8A8A8A] opacity-50" />
            </div>
            <p className="font-medium text-[#4A4A4A] mb-2">아직 아이템이 없어요</p>
            <p className="text-sm text-[#8A8A8A] mb-6 px-8">
              꾸준히 일기를 작성하면<br />
              이음이를 위한 선물을 받을 수 있어요!
            </p>
            
            <div className="bg-white/80 backdrop-blur-sm rounded-[1.5rem] p-6 shadow-sm max-w-xs">
              <h3 className="font-semibold text-[#4A4A4A] mb-3">보상 목록</h3>
              <div className="space-y-2 text-left">
                <div className="flex items-center gap-2 text-sm">
                  <span className="text-lg">🍖</span>
                  <span className="text-[#6A6A6A]">3일 연속 → 츄르</span>
                </div>
                <div className="flex items-center gap-2 text-sm">
                  <span className="text-lg">🧶</span>
                  <span className="text-[#6A6A6A]">5일 연속 → 털실 공</span>
                </div>
                <div className="flex items-center gap-2 text-sm">
                  <span className="text-lg">🐟</span>
                  <span className="text-[#6A6A6A]">7일 연속 → 연어 츄르</span>
                </div>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
