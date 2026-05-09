import { useState, useEffect } from 'react';
import { ChevronLeft, ChevronRight } from 'lucide-react';
import { DiaryEntry, diaryApi } from '../utils/api';
import { EMOTIONS } from '../utils/mockData';

interface CalendarViewProps {
  onDateSelect: (entry: DiaryEntry) => void;
}

export function CalendarView({ onDateSelect }: CalendarViewProps) {
  const [currentDate, setCurrentDate] = useState(new Date());
  const [diaries, setDiaries] = useState<DiaryEntry[]>([]);
  const [loading, setLoading] = useState(false);

  const year = currentDate.getFullYear();
  const month = currentDate.getMonth();

  // 일기 목록 불러오기
  useEffect(() => {
    loadDiaries();
  }, [year, month]);

  const loadDiaries = async () => {
    setLoading(true);
    try {
      const response = await diaryApi.getList(year, month + 1);
      setDiaries(response.items); // DiaryListResponse에서 items 추출
    } catch (error) {
      console.error('Failed to load diaries:', error);
    } finally {
      setLoading(false);
    }
  };

  // 이전 달
  const prevMonth = () => {
    setCurrentDate(new Date(year, month - 1, 1));
  };

  // 다음 달
  const nextMonth = () => {
    setCurrentDate(new Date(year, month + 1, 1));
  };

  // 캘린더 날짜 생성
  const generateCalendar = () => {
    const firstDay = new Date(year, month, 1).getDay();
    const lastDate = new Date(year, month + 1, 0).getDate();
    const prevLastDate = new Date(year, month, 0).getDate();

    const days: Array<{ date: number; isCurrentMonth: boolean; fullDate: string }> = [];

    // 이전 달 날짜
    for (let i = firstDay - 1; i >= 0; i--) {
      days.push({
        date: prevLastDate - i,
        isCurrentMonth: false,
        fullDate: `${year}-${String(month).padStart(2, '0')}-${String(prevLastDate - i).padStart(2, '0')}`,
      });
    }

    // 현재 달 날짜
    for (let i = 1; i <= lastDate; i++) {
      days.push({
        date: i,
        isCurrentMonth: true,
        fullDate: `${year}-${String(month + 1).padStart(2, '0')}-${String(i).padStart(2, '0')}`,
      });
    }

    // 다음 달 날짜 (6주 채우기)
    const remainingDays = 42 - days.length;
    for (let i = 1; i <= remainingDays; i++) {
      days.push({
        date: i,
        isCurrentMonth: false,
        fullDate: `${year}-${String(month + 2).padStart(2, '0')}-${String(i).padStart(2, '0')}`,
      });
    }

    return days;
  };

  // 해당 날짜의 일기 가져오기
  const getDiaryForDate = (dateStr: string) => {
    return diaries.find((d) => d.date === dateStr);
  };

  // 감정에 해당하는 이모지 가져오기
  const getEmotionEmoji = (emotionName: string) => {
    const emotion = EMOTIONS.find((e) => e.name === emotionName);
    return emotion?.emoji || '📝';
  };

  const calendarDays = generateCalendar();
  const today = new Date().toISOString().split('T')[0];

  return (
    <div className="flex flex-col h-full max-w-lg mx-auto bg-[#FAF8F5]">
      {/* 헤더 */}
      <div className="bg-white/80 backdrop-blur-sm border-b border-[rgba(0,0,0,0.06)] px-4 py-4">
        <div className="flex items-center justify-between mb-4">
          <button
            onClick={prevMonth}
            className="p-2 hover:bg-[#F5F3F0] rounded-full transition-colors"
          >
            <ChevronLeft className="w-5 h-5 text-[#4A4A4A]" />
          </button>
          <div className="text-center">
            <h2 className="font-semibold text-[#4A4A4A]">
              {year}년 {month + 1}월
            </h2>
            <p className="text-xs text-[#8A8A8A] mt-0.5">감정 캘린더</p>
          </div>
          <button
            onClick={nextMonth}
            className="p-2 hover:bg-[#F5F3F0] rounded-full transition-colors"
          >
            <ChevronRight className="w-5 h-5 text-[#4A4A4A]" />
          </button>
        </div>

        {/* 요일 헤더 */}
        <div className="grid grid-cols-7 gap-1 text-center text-sm font-medium text-[#8A8A8A]">
          {['일', '월', '화', '수', '목', '금', '토'].map((day, idx) => (
            <div key={day} className={`py-2 ${idx === 0 ? 'text-[#FF9B9B]' : idx === 6 ? 'text-[#B4D4FF]' : ''}`}>
              {day}
            </div>
          ))}
        </div>
      </div>

      {/* 캘린더 그리드 */}
      <div className="flex-1 overflow-y-auto px-4 py-4">
        {loading ? (
          <div className="flex items-center justify-center h-full">
            <div className="text-[#8A8A8A]">로딩 중...</div>
          </div>
        ) : (
          <div className="grid grid-cols-7 gap-2">
            {calendarDays.map((day, index) => {
              const diary = getDiaryForDate(day.fullDate);
              const isToday = day.fullDate === today;

              return (
                <button
                  key={index}
                  onClick={() => diary && onDateSelect(diary)}
                  disabled={!day.isCurrentMonth || !diary}
                  className={`aspect-square flex flex-col items-center justify-center rounded-2xl transition-all ${
                    !day.isCurrentMonth
                      ? 'text-[#D0D0D0]'
                      : isToday
                      ? 'bg-gradient-to-br from-[#FFB4B4] to-[#FFDEB4] text-[#4A4A4A] font-semibold shadow-md scale-105'
                      : diary
                      ? 'bg-white hover:bg-[#F5F3F0] cursor-pointer shadow-sm hover:shadow-md hover:scale-105'
                      : 'hover:bg-white/50 text-[#4A4A4A]'
                  }`}
                >
                  <span className={`text-xs ${!day.isCurrentMonth ? 'opacity-30' : ''} ${isToday ? 'font-bold' : ''}`}>
                    {day.date}
                  </span>
                  {diary && day.isCurrentMonth && (
                    <span className="text-2xl mt-1">
                      {getEmotionEmoji(diary.emotion)}
                    </span>
                  )}
                </button>
              );
            })}
          </div>
        )}

        {/* 이음이 안내 */}
        <div className="mt-6 bg-[#FFDEB4]/20 rounded-[1.5rem] p-5 shadow-sm">
          <div className="flex gap-3">
            <div className="text-xl flex-shrink-0">🤗</div>
            <div>
              <p className="text-sm text-[#6A6A6A] leading-relaxed">
                <span className="font-semibold text-[#4A4A4A]">이음이 tip:</span> 날짜를 눌러 과거의 일기를 다시 읽어보세요. 그때의 감정을 되돌아보는 것도 좋은 습관이에요!
              </p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}