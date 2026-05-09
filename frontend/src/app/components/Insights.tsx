import { useState, useEffect } from 'react';
import { Lightbulb, Calendar, TrendingUp, Sparkles } from 'lucide-react';
import { DailyInsight, WeeklyReport, insightApi } from '../utils/api';

export function Insights() {
  const [activeTab, setActiveTab] = useState<'daily' | 'weekly'>('daily');
  const [dailyInsight, setDailyInsight] = useState<DailyInsight | null>(null);
  const [weeklyReport, setWeeklyReport] = useState<WeeklyReport | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (activeTab === 'daily') {
      loadDailyInsight();
    } else {
      loadWeeklyReport();
    }
  }, [activeTab]);

  const loadDailyInsight = async () => {
    setLoading(true);
    try {
      const today = new Date().toISOString().split('T')[0];
      const data = await insightApi.getDaily(today);
      setDailyInsight(data);
    } catch (error) {
      console.error('Failed to load daily insight:', error);
    } finally {
      setLoading(false);
    }
  };

  const loadWeeklyReport = async () => {
    setLoading(true);
    try {
      const data = await insightApi.getWeekly();
      setWeeklyReport(data);
    } catch (error) {
      console.error('Failed to load weekly report:', error);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex flex-col h-full max-w-lg mx-auto bg-[#FAF8F5]">
      {/* 헤더 */}
      <div className="bg-white/80 backdrop-blur-sm border-b border-[rgba(0,0,0,0.06)] px-4 py-4">
        <div className="flex items-center gap-3 mb-4">
          <div className="w-10 h-10 bg-gradient-to-br from-[#FFB4B4] to-[#FFDEB4] rounded-full flex items-center justify-center text-xl shadow-sm">
            🤗
          </div>
          <div>
            <h1 className="font-semibold text-[#4A4A4A]">AI 인사이트</h1>
            <p className="text-xs text-[#8A8A8A]">이음이가 준비한 리포트</p>
          </div>
        </div>

        {/* 탭 */}
        <div className="flex gap-2">
          <button
            onClick={() => setActiveTab('daily')}
            className={`flex-1 py-2.5 rounded-[1rem] text-sm font-medium transition-all ${
              activeTab === 'daily'
                ? 'bg-gradient-to-r from-[#FFB4B4] to-[#FFDEB4] text-[#4A4A4A] shadow-sm'
                : 'bg-[#F5F3F0] text-[#6A6A6A] hover:bg-[#E8E6E3]'
            }`}
          >
            ✨ 일일
          </button>
          <button
            onClick={() => setActiveTab('weekly')}
            className={`flex-1 py-2.5 rounded-[1rem] text-sm font-medium transition-all ${
              activeTab === 'weekly'
                ? 'bg-gradient-to-r from-[#FFB4B4] to-[#FFDEB4] text-[#4A4A4A] shadow-sm'
                : 'bg-[#F5F3F0] text-[#6A6A6A] hover:bg-[#E8E6E3]'
            }`}
          >
            📊 주간
          </button>
        </div>
      </div>

      {/* 내용 */}
      <div className="flex-1 overflow-y-auto px-4 py-6 space-y-4">
        {loading ? (
          <div className="flex items-center justify-center h-full">
            <div className="text-[#8A8A8A]">로딩 중...</div>
          </div>
        ) : activeTab === 'daily' && dailyInsight ? (
          <>
            {/* 일일 인사이트 */}
            <div className="bg-gradient-to-br from-[#B4D4FF] to-[#D4E4FF] rounded-[2rem] p-6 shadow-md">
              <div className="flex items-center gap-3 mb-4">
                <div className="w-12 h-12 bg-white/50 rounded-full flex items-center justify-center text-2xl shadow-sm">
                  🤗
                </div>
                <div>
                  <h2 className="font-bold text-[#4A4A4A]">오늘의 인사이트</h2>
                  <p className="text-xs text-[#4A4A4A]/70">
                    {new Date(dailyInsight.date).toLocaleDateString('ko-KR', {
                      month: 'short',
                      day: 'numeric',
                    })}
                  </p>
                </div>
              </div>
              <p className="text-base leading-relaxed text-[#4A4A4A]">
                {dailyInsight.insight}
              </p>
            </div>

            {/* 행동 팁 */}
            <div className="bg-white/80 backdrop-blur-sm rounded-[2rem] p-6 shadow-sm">
              <div className="flex items-center gap-3 mb-4">
                <div className="w-10 h-10 bg-[#FFDEB4]/30 rounded-full flex items-center justify-center text-xl">
                  💡
                </div>
                <h3 className="font-semibold text-[#4A4A4A]">이음이의 조언</h3>
              </div>
              <p className="text-sm text-[#6A6A6A] leading-relaxed">{dailyInsight.tip}</p>
            </div>
          </>
        ) : activeTab === 'weekly' && weeklyReport ? (
          <>
            {/* 주간 요약 */}
            <div className="bg-gradient-to-br from-[#D4B4FF] to-[#E4D4FF] rounded-[2rem] p-6 shadow-md">
              <div className="flex items-center gap-3 mb-4">
                <div className="w-12 h-12 bg-white/50 rounded-full flex items-center justify-center text-2xl shadow-sm">
                  🤗
                </div>
                <div>
                  <h2 className="font-bold text-[#4A4A4A]">주간 리포트</h2>
                  <p className="text-xs text-[#4A4A4A]/70">
                    {new Date(weeklyReport.startDate).toLocaleDateString('ko-KR', {
                      month: 'short',
                      day: 'numeric',
                    })}{' '}
                    -{' '}
                    {new Date(weeklyReport.endDate).toLocaleDateString('ko-KR', {
                      month: 'short',
                      day: 'numeric',
                    })}
                  </p>
                </div>
              </div>
              <p className="text-base leading-relaxed text-[#4A4A4A]">
                {weeklyReport.summary}
              </p>
            </div>

            {/* 주요 감정 */}
            <div className="bg-white/80 backdrop-blur-sm rounded-[2rem] p-6 shadow-sm">
              <h3 className="font-semibold mb-4 text-[#4A4A4A] flex items-center gap-2">
                <span>🏆</span> 주요 감정 TOP 3
              </h3>
              <div className="flex gap-3">
                {weeklyReport.topEmotions.map((emotion, index) => (
                  <div
                    key={index}
                    className="flex-1 bg-gradient-to-br from-[#FFB4B4]/20 to-[#FFDEB4]/20 rounded-2xl p-4 text-center"
                  >
                    <div className="text-3xl mb-2">{index === 0 ? '🥇' : index === 1 ? '🥈' : '🥉'}</div>
                    <p className="text-sm font-semibold text-[#4A4A4A]">{emotion}</p>
                  </div>
                ))}
              </div>
            </div>

            {/* 평균 만족도 */}
            <div className="bg-white/80 backdrop-blur-sm rounded-[2rem] p-6 shadow-sm">
              <h3 className="font-semibold mb-4 text-[#4A4A4A] flex items-center gap-2">
                <span>💖</span> 평균 만족도
              </h3>
              <div className="flex items-center gap-4">
                <div className="flex-1 bg-[#F5F3F0] rounded-full h-4 overflow-hidden">
                  <div
                    className="bg-gradient-to-r from-[#FFB4B4] to-[#FFDEB4] h-full rounded-full transition-all"
                    style={{ width: `${weeklyReport.avgSatisfaction}%` }}
                  />
                </div>
                <span className="font-bold text-2xl text-[#FFB4B4] min-w-[4rem] text-right">
                  {weeklyReport.avgSatisfaction}점
                </span>
              </div>
            </div>

            {/* 행동 팁 */}
            <div className="bg-white/80 backdrop-blur-sm rounded-[2rem] p-6 shadow-sm">
              <div className="flex items-center gap-3 mb-4">
                <div className="w-10 h-10 bg-[#FFDEB4]/30 rounded-full flex items-center justify-center text-xl">
                  💡
                </div>
                <h3 className="font-semibold text-[#4A4A4A]">이음이의 추천</h3>
              </div>
              <ul className="space-y-3">
                {weeklyReport.tips.map((tip, index) => (
                  <li key={index} className="flex items-start gap-3">
                    <span className="flex-shrink-0 w-6 h-6 bg-gradient-to-br from-[#FFB4B4] to-[#FFDEB4] text-white rounded-full flex items-center justify-center text-xs font-bold shadow-sm">
                      {index + 1}
                    </span>
                    <span className="text-sm text-[#6A6A6A] leading-relaxed">{tip}</span>
                  </li>
                ))}
              </ul>
            </div>
          </>
        ) : (
          <div className="flex flex-col items-center justify-center h-full text-[#8A8A8A]">
            <div className="w-20 h-20 bg-gradient-to-br from-[#FFB4B4] to-[#FFDEB4] rounded-full flex items-center justify-center text-4xl mb-4 opacity-50">
              🤗
            </div>
            <p className="font-medium">아직 인사이트가 없어요</p>
            <p className="text-sm mt-2">일기를 작성하면 분석을 시작해요!</p>
          </div>
        )}
      </div>
    </div>
  );
}