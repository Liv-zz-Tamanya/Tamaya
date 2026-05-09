import { useState } from 'react';
import { X, Trash2 } from 'lucide-react';
import { DiaryEntry, diaryApi } from '../utils/api';
import { EMOTIONS } from '../utils/mockData';

interface DiaryDetailProps {
  diary: DiaryEntry;
  onClose: () => void;
  onDelete: () => void;
}

export function DiaryDetail({ diary, onClose, onDelete }: DiaryDetailProps) {
  const [isDeleting, setIsDeleting] = useState(false);

  const handleDelete = async () => {
    if (!confirm('일기를 삭제하시겠습니까? 이 작업은 되돌릴 수 없습니다.')) {
      return;
    }

    setIsDeleting(true);
    try {
      await diaryApi.delete(diary.id);
      onDelete();
    } catch (error) {
      console.error('Failed to delete diary:', error);
      alert('일기 삭제에 실패했습니다.');
    } finally {
      setIsDeleting(false);
    }
  };

  const getEmotionEmoji = (emotionName: string) => {
    const emotion = EMOTIONS.find((e) => e.name === emotionName);
    return emotion?.emoji || '📝';
  };

  const formatDate = (dateStr: string) => {
    const date = new Date(dateStr);
    return `${date.getFullYear()}년 ${date.getMonth() + 1}월 ${date.getDate()}일`;
  };

  return (
    <div className="fixed inset-0 bg-black/30 z-50 flex items-end sm:items-center justify-center">
      <div className="bg-white w-full max-w-lg rounded-t-[2rem] sm:rounded-[2rem] max-h-[90vh] overflow-hidden flex flex-col animate-slide-up">
        {/* 헤더 */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-[rgba(0,0,0,0.06)]">
          <h2 className="font-semibold text-[#4A4A4A]">{formatDate(diary.date)}</h2>
          <div className="flex items-center gap-2">
            <button
              onClick={handleDelete}
              disabled={isDeleting}
              className="p-2 hover:bg-[#FFE5E5] rounded-full transition-colors text-[#FF9B9B]"
            >
              <Trash2 className="w-5 h-5" />
            </button>
            <button
              onClick={onClose}
              className="p-2 hover:bg-[#F5F3F0] rounded-full transition-colors text-[#4A4A4A]"
            >
              <X className="w-5 h-5" />
            </button>
          </div>
        </div>

        {/* 내용 */}
        <div className="flex-1 overflow-y-auto px-6 py-6 space-y-6">
          {/* 감정 */}
          <div>
            <h3 className="text-sm font-medium text-[#8A8A8A] mb-3">오늘의 감정</h3>
            <div className="flex flex-wrap gap-2">
              <span className="px-3 py-2 bg-[#FFB4B4]/20 text-[#4A4A4A] rounded-full text-sm">
                {getEmotionEmoji(diary.emotion)} {diary.emotion}
              </span>
            </div>
          </div>

          {/* 만족도 */}
          <div>
            <h3 className="text-sm font-medium text-[#8A8A8A] mb-3">하루 만족도</h3>
            <div className="flex items-center gap-4">
              <div className="flex-1 bg-[#F5F3F0] rounded-full h-3 overflow-hidden">
                <div
                  className="bg-[#FFB4B4] h-full rounded-full transition-all"
                  style={{ width: `${diary.satisfaction}%` }}
                />
              </div>
              <span className="font-semibold text-[#FFB4B4] min-w-[3rem] text-right">
                {diary.satisfaction}점
              </span>
            </div>
          </div>

          {/* 일기 내용 */}
          <div>
            <h3 className="text-sm font-medium text-[#8A8A8A] mb-3">일기</h3>
            <p className="text-[#4A4A4A] leading-relaxed whitespace-pre-wrap">
              {diary.content}
            </p>
          </div>

          {/* 작성 시간 */}
          <div className="text-xs text-[#AFAFAF] text-right">
            작성: {new Date(diary.createdAt).toLocaleString('ko-KR')}
          </div>
        </div>
      </div>
    </div>
  );
}