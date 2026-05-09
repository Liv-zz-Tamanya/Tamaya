import { useState, useEffect } from 'react';
import { BarChart3, TrendingUp } from 'lucide-react';
import { EmotionStats, emotionApi } from '../utils/api';

export function Statistics() {
  const [period, setPeriod] = useState<'week' | 'month'>('week');
  const [stats, setStats] = useState<EmotionStats | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    loadStats();
  }, [period]);

  const loadStats = async () => {
    setLoading(true);
    try {
      const data = await emotionApi.getStats(period);
      setStats(data);
    } catch (error) {
      console.error('Failed to load stats:', error);
    } finally {
      setLoading(false);
    }
  };

  const maxCount = stats?.emotions[0]?.count || 1;

  return (
    <div className="flex flex-col h-full max-w-lg mx-auto bg-[#FAF8F5]">
      {/* 헤더 */}
      <div className="bg-white/80 backdrop-blur-sm border-b border-[rgba(0,0,0,0.06)] px-4 py-4">
        <div className="flex items-center gap-3 mb-4">
          <div className="w-10 h-10 bg-gradient-to-br from-[#FFB4B4] to-[#FFDEB4] rounded-full flex items-center justify-center text-xl shadow-sm">
            🤗
          </div>
          <div>
            <h1 className="font-semibold text-[#4A4A4A]">감정 분석</h1>
            <p className="text-xs text-[#8A8A8A]">이음이�� 분석한 통계예요</p>
          </div>
        </div>

        {/* 기간 선택 */}
        <div className="flex gap-2">
          <button
            onClick={() => setPeriod('week')}
            className={`flex-1 py-2.5 rounded-[1rem] text-sm font-medium transition-all ${
              period === 'week'
                ? 'bg-gradient-to-r from-[#FFB4B4] to-[#FFDEB4] text-[#4A4A4A] shadow-sm'
                : 'bg-[#F5F3F0] text-[#6A6A6A] hover:bg-[#E8E6E3]'
            }`}
          >
            📅 주간
          </button>
          <button
            onClick={() => setPeriod('month')}
            className={`flex-1 py-2.5 rounded-[1rem] text-sm font-medium transition-all ${
              period === 'month'
                ? 'bg-gradient-to-r from-[#FFB4B4] to-[#FFDEB4] text-[#4A4A4A] shadow-sm'
                : 'bg-[#F5F3F0] text-[#6A6A6A] hover:bg-[#E8E6E3]'
            }`}
          >
            📆 월간
          </button>
        </div>
      </div>

      {/* 통계 내용 */}
      <div className="flex-1 overflow-y-auto px-4 py-6 space-y-4">
        {loading ? (
          <div className="flex items-center justify-center h-full">
            <div className="text-[#8A8A8A]">로딩 중...</div>
          </div>
        ) : stats ? (
          <>
            {/* 요약 카드 */}
            <div className="grid grid-cols-2 gap-3">
              <div className="bg-white/80 backdrop-blur-sm rounded-[1.5rem] p-5 shadow-sm">
                <div className="flex items-center gap-2 text-[#8A8A8A] mb-2">
                  <BarChart3 className="w-4 h-4" />
                  <span className="text-xs">기록 일수</span>
                </div>
                <p className="font-bold text-3xl text-[#4A4A4A]">{stats.totalDays}</p>
                <p className="text-xs text-[#8A8A8A] mt-1">일</p>
              </div>

              <div className="bg-white/80 backdrop-blur-sm rounded-[1.5rem] p-5 shadow-sm">
                <div className="flex items-center gap-2 text-[#8A8A8A] mb-2">
                  <TrendingUp className="w-4 h-4" />
                  <span className="text-xs">평균 만족도</span>
                </div>
                <p className="font-bold text-3xl text-[#FFB4B4]">
                  {stats.satisfactionAvg}
                </p>
                <p className="text-xs text-[#8A8A8A] mt-1">점</p>
              </div>
            </div>

            {/* 감정 분포 */}
            <div className="bg-white/80 backdrop-blur-sm rounded-[1.5rem] p-5 shadow-sm">
              <h2 className="font-semibold mb-4 text-[#4A4A4A] flex items-center gap-2">
                <span>📊</span> 감정 분포
              </h2>
              <div className="space-y-4">
                {stats.emotions.map((emotion, index) => (
                  <div key={index}>
                    <div className="flex items-center justify-between mb-2">
                      <div className="flex items-center gap-2">
                        <span className="text-2xl">{emotion.emoji}</span>
                        <span className="font-medium text-[#4A4A4A]">{emotion.name}</span>
                      </div>
                      <span className="text-sm text-[#8A8A8A] font-medium">{emotion.count}회</span>
                    </div>
                    <div className="bg-[#F5F3F0] rounded-full h-2.5 overflow-hidden">
                      <div
                        className="bg-gradient-to-r from-[#FFB4B4] to-[#FFDEB4] h-full rounded-full transition-all duration-500"
                        style={{ width: `${(emotion.count / maxCount) * 100}%` }}
                      />
                    </div>
                  </div>
                ))}
              </div>
            </div>

            {/* 이음이 분석 */}
            <div className="bg-gradient-to-br from-[#B4D4FF] to-[#D4B4FF] rounded-[2rem] p-6 shadow-sm">
              <div className="flex gap-3 mb-3">
                <div className="text-2xl flex-shrink-0">🤗</div>
                <h3 className="font-semibold text-[#4A4A4A]">이음이의 분석</h3>
              </div>
              <p className="text-sm text-[#4A4A4A] leading-relaxed">
                {period === 'week' ? '이번 주' : '이번 달'}에는{' '}
                <span className="font-bold">{stats.emotions[0]?.name}</span> 감정을 가장
                많이 느끼셨네요. 평균 만족도는{' '}
                <span className="font-bold">{stats.satisfactionAvg}점</span>으로{' '}
                {stats.satisfactionAvg >= 70
                  ? '긍정적인 상태를 잘 유지하고 계세요! 👏'
                  : '조금 더 나은 하루를 위해 작은 것부터 시작해보아요. 💪'}
              </p>
            </div>
          </>
        ) : (
          <div className="flex flex-col items-center justify-center h-full text-[#8A8A8A]">
            <BarChart3 className="w-16 h-16 mb-4 opacity-50" />
            <p>아직 통계 데이터가 없어요</p>
            <p className="text-sm mt-2">일기를 작성하면 분석을 시작해요!</p>
          </div>
        )}
      </div>
    </div>
  );
}