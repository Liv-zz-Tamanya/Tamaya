import { X, Gift, Star } from 'lucide-react';
import { Reward } from '../utils/rewardSystem';
import { EumiCharacter } from './EumiCharacter';

interface RewardModalProps {
  rewards: Reward[];
  onClose: () => void;
  onClaim: (rewardId: string) => void;
}

export function RewardModal({ rewards, onClose, onClaim }: RewardModalProps) {
  if (rewards.length === 0) return null;

  return (
    <div className="fixed inset-0 bg-black/40 z-50 flex items-center justify-center p-4">
      <div className="bg-white w-full max-w-md rounded-[2rem] overflow-hidden animate-scale-up shadow-2xl">
        {/* 헤더 */}
        <div className="bg-gradient-to-r from-[#FFB4B4] to-[#FFDEB4] px-6 py-6 text-center relative">
          <button
            onClick={onClose}
            className="absolute top-4 right-4 p-2 hover:bg-white/20 rounded-full transition-colors"
          >
            <X className="w-5 h-5 text-[#4A4A4A]" />
          </button>
          
          <div className="flex justify-center mb-4">
            <EumiCharacter size="xl" mood="excited" />
          </div>
          
          <h2 className="font-bold text-xl text-[#4A4A4A] mb-2">
            🎉 축하해요!
          </h2>
          <p className="text-sm text-[#4A4A4A]/80">
            새로운 보상을 받았어요!
          </p>
        </div>

        {/* 보상 목록 */}
        <div className="px-6 py-6 space-y-3 max-h-[400px] overflow-y-auto">
          {rewards.map((reward) => (
            <div
              key={reward.id}
              className="bg-gradient-to-br from-[#F5F3F0] to-[#FAF8F5] rounded-[1.5rem] p-5 border-2 border-[#FFB4B4]/30"
            >
              <div className="flex items-center gap-4 mb-3">
                <div className="w-16 h-16 bg-white rounded-2xl flex items-center justify-center text-4xl shadow-sm">
                  {reward.emoji}
                </div>
                <div className="flex-1">
                  <div className="flex items-center gap-2 mb-1">
                    <h3 className="font-bold text-[#4A4A4A]">{reward.name}</h3>
                    {reward.type === 'snack' && (
                      <span className="px-2 py-0.5 bg-[#FFB4B4]/20 text-[#4A4A4A] text-xs rounded-full">
                        간식
                      </span>
                    )}
                    {reward.type === 'toy' && (
                      <span className="px-2 py-0.5 bg-[#B4D4FF]/20 text-[#4A4A4A] text-xs rounded-full">
                        장난감
                      </span>
                    )}
                  </div>
                  <p className="text-sm text-[#6A6A6A]">{reward.description}</p>
                </div>
              </div>
              
              <button
                onClick={() => onClaim(reward.id)}
                className="w-full bg-gradient-to-r from-[#FFB4B4] to-[#FFDEB4] text-[#4A4A4A] py-3 rounded-[1rem] font-semibold hover:shadow-md transition-all shadow-sm flex items-center justify-center gap-2"
              >
                <Gift className="w-4 h-4" />
                받기
              </button>
            </div>
          ))}
        </div>

        {/* 푸터 */}
        <div className="px-6 py-4 bg-[#FAF8F5] border-t border-[rgba(0,0,0,0.06)]">
          <p className="text-xs text-center text-[#8A8A8A]">
            💡 인벤토리에서 이음이와 함께 사용할 수 있어요
          </p>
        </div>
      </div>
    </div>
  );
}
