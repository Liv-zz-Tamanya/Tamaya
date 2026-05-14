import { useState, useEffect } from "react";
// DEC-023 동시접속 토스트는 BE 통합 시점에 다시 활성화 (sonner optimize reload + Toaster throw 이슈로 임시 제거)
// import { Toaster } from "sonner";
import { Home } from "./components/Home";
import { ChatDiary } from "./components/ChatDiary";
import { CalendarView } from "./components/CalendarView";
import { Statistics } from "./components/Statistics";
import { Insights } from "./components/Insights";
import { InventoryPage } from "./components/InventoryPage";
import { WelcomeScreen } from "./components/WelcomeScreen";
import { BottomNav } from "./components/BottomNav";
import { DiaryDetail } from "./components/DiaryDetail";
import { RewardModal } from "./components/RewardModal";
import { Diary } from "./utils/api";
import {
  getNewRewards,
  claimReward,
  getProgress,
} from "./utils/rewardSystem";

type Page =
  | "home"
  | "diary"
  | "calendar"
  | "statistics"
  | "insights"
  | "inventory";

function App() {
  const [showWelcome, setShowWelcome] = useState(false);
  const [currentPage, setCurrentPage] = useState<Page>("home");
  const [selectedDiary, setSelectedDiary] =
    useState<Diary | null>(null);
  const [newRewards, setNewRewards] = useState<any[]>([]);

  // 첫 방문 확인
  useEffect(() => {
    const hasVisited = localStorage.getItem("hasVisited");
    if (!hasVisited) {
      setShowWelcome(true);
    }
  }, []);

  const handleWelcomeComplete = () => {
    localStorage.setItem("hasVisited", "true");
    setShowWelcome(false);
  };

  const handleStartDiary = () => {
    setCurrentPage("diary");
  };

  const handleNavigate = (page: string) => {
    setCurrentPage(page as Page);
  };

  const handleDiaryComplete = () => {
    // 보상 확인
    const progress = getProgress();
    const rewards = getNewRewards(progress);

    if (rewards.length > 0) {
      setNewRewards(rewards);
    }

    setCurrentPage("home");
  };

  const handleDateSelect = (diary: Diary) => {
    setSelectedDiary(diary);
  };

  const handleDiaryDelete = () => {
    setSelectedDiary(null);
    setCurrentPage("calendar");
  };

  const handleClaimReward = (rewardId: string) => {
    claimReward(rewardId);
    setNewRewards((prev) =>
      prev.filter((r) => r.id !== rewardId),
    );
  };

  // 현재 시간 (상태바용)
  const currentTime = new Date().toLocaleTimeString("ko-KR", {
    hour: "2-digit",
    minute: "2-digit",
  });

  // 온보딩 화면 표시
  if (showWelcome) {
    return (
      <div className="min-h-screen bg-[#f3f0e9] flex justify-center items-center p-0 md:p-8 font-main antialiased overflow-hidden">
        <div className="w-full max-w-md h-screen md:h-[840px] bg-white relative md:rounded-[3rem] shadow-[0_40px_80px_-20px_rgba(0,0,0,0.1)] overflow-hidden flex flex-col border-2 border-white">
          <WelcomeScreen onComplete={handleWelcomeComplete} />
        </div>
      </div>
    );
  }

  return (
    <>
    {/* DEC-023 동시접속 1세션 — sonner Toaster 임시 제거 (auto-reload + throw 이슈) */}
    <div className="min-h-screen bg-[#f3f0e9] flex justify-center items-center p-0 md:p-8 font-main antialiased overflow-hidden">
      {/* 모바일 프레임 */}
      <div className="w-full max-w-md h-screen md:h-[840px] bg-gradient-to-br from-[#FAF8F5] to-[#F5E6D3] relative md:rounded-[3rem] shadow-[0_40px_80px_-20px_rgba(0,0,0,0.1)] overflow-hidden flex flex-col transition-all duration-700 border-2 border-white">
        
        {/* 상태바 (iOS 스타일) */}
        <div className="h-10 w-full flex justify-between items-center px-8 text-[9px] font-black text-stone-400 tracking-widest pt-3 z-20 pointer-events-none font-sans-system uppercase">
          <span>{currentTime}</span>
          <div className="flex items-center space-x-2">
            <div className="flex items-center space-x-0.5">
              <div className="w-0.5 h-2 bg-stone-300 rounded-full"></div>
              <div className="w-0.5 h-2.5 bg-stone-300 rounded-full"></div>
              <div className="w-0.5 h-3 bg-stone-300 rounded-full"></div>
              <div className="w-0.5 h-3.5 bg-stone-400 rounded-full"></div>
            </div>
            <span className="text-stone-400">100%</span>
          </div>
        </div>

        {/* 메인 콘텐츠 */}
        <main className="flex-1 overflow-hidden pb-20">
          {currentPage === "home" && (
            <Home
              onStartDiary={handleStartDiary}
              onNavigate={handleNavigate}
            />
          )}

          {currentPage === "diary" && (
            <ChatDiary onComplete={handleDiaryComplete} />
          )}

          {currentPage === "calendar" && (
            <CalendarView onDateSelect={handleDateSelect} />
          )}

          {currentPage === "statistics" && <Statistics />}

          {currentPage === "insights" && <Insights />}

          {currentPage === "inventory" && <InventoryPage />}
        </main>

        {/* 하단 네비게이션 */}
        <BottomNav
          currentPage={currentPage}
          onNavigate={handleNavigate}
        />

        {/* 일기 상세 모달 */}
        {selectedDiary && (
          <DiaryDetail
            diary={selectedDiary}
            onClose={() => setSelectedDiary(null)}
            onDelete={handleDiaryDelete}
          />
        )}

        {/* 보상 모달 */}
        {newRewards.length > 0 && (
          <RewardModal
            rewards={newRewards}
            onClose={() => setNewRewards([])}
            onClaim={handleClaimReward}
          />
        )}
      </div>
    </div>
    </>
  );
}

export default App;