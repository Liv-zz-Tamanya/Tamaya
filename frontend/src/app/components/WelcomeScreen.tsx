import { useState } from 'react';
import { ChevronRight, Coffee, BookOpen, BarChart3, User, Target } from 'lucide-react';
import { ButlerCatHappy, WineGlassIcon, QuillIcon, DiaryBookIcon } from './ButlerIcons';
import { saveUserProfile } from '../utils/userProfile';

interface WelcomeScreenProps {
  onComplete: () => void;
}

export function WelcomeScreen({ onComplete }: WelcomeScreenProps) {
  const [currentStep, setCurrentStep] = useState(0);
  const [selectedEmotions, setSelectedEmotions] = useState<string[]>([]);
  const [nickname, setNickname] = useState('');
  const [dailyGoal, setDailyGoal] = useState('');

  const handleNext = () => {
    if (currentStep < 3) {
      // Step 2에서 Step 3로 넘어갈 때 감정 저장
      if (currentStep === 2 && selectedEmotions.length > 0) {
        saveUserProfile({ preferredEmotions: selectedEmotions });
      }
      setCurrentStep(currentStep + 1);
    } else {
      // Step 3: 사용자 정보 저장 및 완료
      saveUserProfile({
        nickname: nickname || '고객님',
        dailyGoal: dailyGoal || '하루를 돌아보기',
        preferredEmotions: selectedEmotions,
      });
      localStorage.setItem('hasVisited', 'true');
      onComplete();
    }
  };

  const handleSkip = () => {
    localStorage.setItem('hasVisited', 'true');
    onComplete();
  };

  const toggleEmotion = (id: string) => {
    setSelectedEmotions(prev =>
      prev.includes(id)
        ? prev.filter(e => e !== id)
        : [...prev, id]
    );
  };

  // 각 단계별 버튼 활성화 조건
  const canProceed = () => {
    if (currentStep === 2) {
      return selectedEmotions.length > 0;
    }
    if (currentStep === 3) {
      return nickname.trim().length > 0;
    }
    return true;
  };

  const getButtonText = () => {
    if (currentStep === 3) return '시작하기';
    if (currentStep === 2) return '다음';
    return '다음';
  };

  return (
    <div className="h-full flex flex-col bg-gradient-warm relative overflow-hidden">
      {/* 배경 장식 - 서브틀하게 */}
      <div className="absolute inset-0 opacity-[0.03] pointer-events-none">
        <div className="absolute top-20 left-10 w-64 h-64 bg-[#A47C4B] rounded-full blur-[100px]"></div>
        <div className="absolute bottom-20 right-10 w-80 h-80 bg-[#7B4B5A] rounded-full blur-[120px]"></div>
      </div>

      {/* 온보딩 단계 */}
      <div className="flex-1 relative z-10">
        {currentStep === 0 && <WelcomeStep1 />}
        {currentStep === 1 && <WelcomeStep2 />}
        {currentStep === 2 && (
          <WelcomeStep3 
            selectedEmotions={selectedEmotions} 
            onToggleEmotion={toggleEmotion} 
          />
        )}
        {currentStep === 3 && (
          <WelcomeStep4
            nickname={nickname}
            setNickname={setNickname}
            dailyGoal={dailyGoal}
            setDailyGoal={setDailyGoal}
          />
        )}
      </div>

      {/* 하단 버튼 */}
      <div className="p-6 pb-10 space-y-3 relative z-10">
        <button
          onClick={handleNext}
          disabled={!canProceed()}
          className={`w-full flex items-center justify-center gap-2 group transition-all ${
            !canProceed()
              ? 'bg-[#E5DDD3] text-[#8B7A6A] cursor-not-allowed py-4 rounded-full opacity-50'
              : 'btn-primary'
          }`}
        >
          <span className="font-bold tracking-wide">
            {getButtonText()}
          </span>
          <ChevronRight 
            size={20} 
            className={`transition-transform ${
              !canProceed()
                ? '' 
                : 'group-hover:translate-x-1'
            }`} 
          />
        </button>
        {currentStep < 3 && (
          <button
            onClick={handleSkip}
            className="w-full py-3 text-[#5A4A3A] font-medium text-sm hover:text-[#2C2419] transition-colors"
          >
            건너뛰기
          </button>
        )}
      </div>

      {/* 페이지 인디케이터 */}
      <div className="absolute bottom-28 left-0 right-0 flex justify-center gap-2 z-10">
        {[0, 1, 2, 3].map((step) => (
          <div
            key={step}
            className={`h-1.5 rounded-full transition-all duration-500 ${
              step === currentStep
                ? 'w-8 bg-[#2C2419]'
                : 'w-1.5 bg-[#D4C4B4]'
            }`}
          />
        ))}
      </div>
    </div>
  );
}

// Step 1: Welcome
function WelcomeStep1() {
  return (
    <div className="flex-1 flex flex-col justify-center items-center px-6 pb-32 text-center">
      {/* 메인 일러스트 */}
      <div className="relative mb-12">
        <div className="w-64 h-64 mx-auto relative">
          <div className="absolute inset-0 card-butler flex items-center justify-center animate-float">
            <div className="text-center">
              <WineGlassIcon size={80} className="mx-auto mb-4" />
              <div className="w-16 h-1 bg-gradient-accent rounded-full mx-auto"></div>
            </div>
          </div>

          <div className="absolute -top-4 -right-4 w-20 h-20 bg-white rounded-[1.5rem] shadow-[0_4px_20px_rgba(0,0,0,0.08)] flex items-center justify-center animate-float-delayed">
            <QuillIcon size={40} />
          </div>

          <div className="absolute -bottom-4 -left-4 w-24 h-24 bg-white rounded-[1.8rem] shadow-[0_4px_20px_rgba(0,0,0,0.08)] flex items-center justify-center animate-float">
            <DiaryBookIcon size={48} />
          </div>
        </div>

        <div className="absolute top-8 left-8 w-2 h-2 bg-[#A47C4B] rounded-full opacity-40"></div>
        <div className="absolute bottom-12 right-12 w-2.5 h-2.5 bg-[#7B4B5A] rounded-full opacity-30"></div>
      </div>

      {/* 텍스트 — CMO 카피 #1~#3 */}
      <div className="space-y-4 mb-8">
        <div className="inline-block px-5 py-1.5 bg-white/80 rounded-full border border-[#E5DDD3] mb-2">
          <span className="text-xs font-bold text-[#A47C4B] uppercase tracking-widest">
            이음이 만나러 가기
          </span>
        </div>

        <h1 className="text-4xl font-black text-[#2C2419] tracking-tight font-title italic leading-tight">
          Tamanya
        </h1>

        <p className="text-base text-[#5A4A3A] leading-relaxed max-w-xs mx-auto font-diary">
          매일 작은 루틴을 함께 키우는<br />
          나만의 AI 친구
        </p>

        <p className="text-xs text-[#8B7A6A] font-diary">
          감정도 건강도, 내 기기 안에서만 머무릅니다
        </p>
      </div>

      {/* 기능 배지 */}
      <div className="flex gap-2 flex-wrap justify-center max-w-sm">
        <span className="px-4 py-2 bg-white/80 rounded-full text-xs font-semibold text-[#5A4A3A] border border-[#E5DDD3]">
          루틴 키우기
        </span>
        <span className="px-4 py-2 bg-white/80 rounded-full text-xs font-semibold text-[#5A4A3A] border border-[#E5DDD3]">
          감정 기록
        </span>
        <span className="px-4 py-2 bg-white/80 rounded-full text-xs font-semibold text-[#5A4A3A] border border-[#E5DDD3]">
          인사이트
        </span>
      </div>
    </div>
  );
}

// Step 2: 프라이버시 안내 (온보딩 Step 1 — CMO #4~#6)
function WelcomeStep2() {
  const features = [
    {
      icon: Coffee,
      title: '루틴을 함께 키워요',
      description: '이음이와 매일 작은 루틴을 만들어가세요',
      color: 'from-[#A47C4B]/10 to-[#C4966D]/10',
      iconBg: 'bg-gradient-to-br from-[#A47C4B] to-[#C4966D]',
    },
    {
      icon: BookOpen,
      title: '감정을 함께 돌아봐요',
      description: '이음이가 오늘 하루를 같이 정리해줄게',
      color: 'from-[#7B4B5A]/10 to-[#9B6B7A]/10',
      iconBg: 'bg-gradient-to-br from-[#7B4B5A] to-[#9B6B7A]',
    },
    {
      icon: BarChart3,
      title: '인사이트 리포트',
      description: '주간 감정 패턴을 내 기기에서만 확인해요',
      color: 'from-[#4A5C4B]/10 to-[#6A7C6B]/10',
      iconBg: 'bg-gradient-to-br from-[#4A5C4B] to-[#6A7C6B]',
    },
  ];

  return (
    <div className="flex-1 flex flex-col px-6 pt-20 pb-32">
      {/* 헤더 — CMO #4 */}
      <div className="text-center mb-10">
        <div className="inline-block px-4 py-1.5 bg-white/80 border border-[#E5DDD3] rounded-full mb-4">
          <span className="text-xs font-bold text-[#A47C4B] uppercase tracking-wider">
            Privacy First
          </span>
        </div>
        <h2 className="text-3xl font-black text-[#2C2419] mb-2 font-title italic">
          여기서 하는 이야기는<br />네 폰 밖으로 나가지 않아
        </h2>
        <p className="text-sm text-[#5A4A3A] font-diary leading-relaxed">
          서버에 저장하지 않아요.<br />삭제하면 진짜 사라져요.
        </p>
      </div>

      {/* 기능 카드들 */}
      <div className="space-y-4">
        {features.map((feature, index) => {
          const Icon = feature.icon;
          return (
            <div
              key={index}
              className="card-elevated p-6 hover:scale-[1.02] transition-all duration-300 group"
              style={{ animationDelay: `${index * 100}ms` }}
            >
              <div className="flex items-center gap-4">
                <div className={`w-14 h-14 ${feature.iconBg} rounded-[1.2rem] flex items-center justify-center shadow-[0_4px_16px_rgba(0,0,0,0.12)] group-hover:scale-110 transition-transform`}>
                  <Icon className="w-7 h-7 text-white" strokeWidth={2.5} />
                </div>

                <div className="flex-1">
                  <h3 className="font-bold text-[#2C2419] mb-1 text-base">
                    {feature.title}
                  </h3>
                  <p className="text-sm text-[#5A4A3A] leading-relaxed">
                    {feature.description}
                  </p>
                </div>

                <div className="w-8 h-8 bg-[#F7F3EE] border-2 border-[#E5DDD3] rounded-full flex items-center justify-center">
                  <span className="text-xs font-black text-[#A47C4B]">{index + 1}</span>
                </div>
              </div>
            </div>
          );
        })}
      </div>

      {/* 동의 안내 — CMO #6 */}
      <div className="mt-8 text-center">
        <p className="text-xs text-[#8B7A6A] italic font-diary">
          내 기기 안에서만 시작하기
        </p>
      </div>
    </div>
  );
}

// Step 3: 감정 선택 - 절제된 컬러
interface WelcomeStep3Props {
  selectedEmotions: string[];
  onToggleEmotion: (id: string) => void;
}

function WelcomeStep3({ selectedEmotions, onToggleEmotion }: WelcomeStep3Props) {
  const emotions = [
    { id: 'happy', label: '기쁨', emoji: '😊', gradient: 'from-[#A47C4B] to-[#C4966D]' },
    { id: 'calm', label: '평온', emoji: '😌', gradient: 'from-[#4A5C4B] to-[#6A7C6B]' },
    { id: 'love', label: '사랑', emoji: '🥰', gradient: 'from-[#7B4B5A] to-[#9B6B7A]' },
    { id: 'sad', label: '슬픔', emoji: '😢', gradient: 'from-[#5A6B7A] to-[#7A8B9A]' },
    { id: 'angry', label: '화남', emoji: '😠', gradient: 'from-[#8B6239] to-[#AB8259]' },
    { id: 'anxious', label: '불안', emoji: '😰', gradient: 'from-[#6B5A7A] to-[#8B7A9A]' },
  ];

  return (
    <div className="flex-1 flex flex-col px-6 pt-20 pb-32">
      {/* 헤더 — CMO #7~#9 이음이 소개 */}
      <div className="text-center mb-8">
        <div className="inline-block px-4 py-1.5 bg-white/80 border border-[#E5DDD3] rounded-full mb-4">
          <span className="text-xs font-bold text-[#A47C4B] uppercase tracking-wider">
            이음이 소개
          </span>
        </div>
        <h2 className="text-3xl font-black text-[#2C2419] mb-2 font-title italic">
          안녕, 나는 이음이야
        </h2>
        <p className="text-sm text-[#5A4A3A] font-diary leading-relaxed">
          오늘부터 매일 작은 루틴을 같이 키워볼까?<br />
          <span className="text-xs text-[#8B7A6A]">지시하지 않아. 그냥 같이 있어줄게.</span>
        </p>
        <p className="text-xs text-[#8B7A6A] mt-2 font-diary">자주 기록하고 싶은 감정을 선택해줘 (최소 1개)</p>
      </div>

      {/* 감정 그리드 */}
      <div className="grid grid-cols-2 gap-3 mb-6">
        {emotions.map((emotion) => {
          const isSelected = selectedEmotions.includes(emotion.id);
          return (
            <button
              key={emotion.id}
              onClick={() => onToggleEmotion(emotion.id)}
              className={`relative p-6 rounded-[2rem] transition-all duration-300 ${
                isSelected
                  ? 'scale-[1.05] shadow-[0_8px_32px_rgba(44,36,25,0.15)]'
                  : 'shadow-[0_4px_20px_rgba(44,36,25,0.06)]'
              }`}
            >
              {/* 배경 */}
              <div className={`absolute inset-0 rounded-[2rem] ${
                isSelected 
                  ? `bg-gradient-to-br ${emotion.gradient}` 
                  : 'bg-white border-2 border-[#E5DDD3]'
              }`}></div>

              {/* 내용 */}
              <div className="relative flex flex-col items-center gap-3">
                <div className={`text-4xl transition-transform ${isSelected ? 'scale-110' : ''}`}>
                  {emotion.emoji}
                </div>
                <span className={`text-sm font-bold uppercase tracking-wide ${
                  isSelected ? 'text-white' : 'text-[#2C2419]'
                }`}>
                  {emotion.label}
                </span>

                {/* 체크 표시 */}
                {isSelected && (
                  <div className="absolute -top-2 -right-2 w-7 h-7 bg-[#2C2419] rounded-full flex items-center justify-center shadow-[0_2px_12px_rgba(0,0,0,0.3)] animate-slide-up">
                    <svg className="w-4 h-4 text-white" fill="currentColor" viewBox="0 0 20 20">
                      <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
                    </svg>
                  </div>
                )}
              </div>
            </button>
          );
        })}
      </div>

      {/* 피드백 */}
      <div className="text-center">
        {selectedEmotions.length > 0 ? (
          <div className="card-elevated inline-block px-6 py-3">
            <p className="text-sm font-semibold text-[#2C2419]">
              <span className="text-gradient-gold">{selectedEmotions.length}개</span> 감정을 선택했어요
            </p>
          </div>
        ) : (
          <div className="bg-[#FFE4A3]/20 border-2 border-[#D4A574]/30 rounded-[1.5rem] px-6 py-3 inline-block">
            <p className="text-xs text-[#8B7A6A] font-semibold">
              ⚠️ 최소 1개 이상의 감정을 선택해주세요
            </p>
          </div>
        )}
      </div>
    </div>
  );
}

// Step 4: 사용자 정보 입력 - 닉네임과 일일 목표
interface WelcomeStep4Props {
  nickname: string;
  setNickname: (value: string) => void;
  dailyGoal: string;
  setDailyGoal: (value: string) => void;
}

function WelcomeStep4({ nickname, setNickname, dailyGoal, setDailyGoal }: WelcomeStep4Props) {
  return (
    <div className="flex-1 flex flex-col px-6 pt-20 pb-32">
      {/* 헤더 — CMO #10~#12 첫 일기 유도 */}
      <div className="text-center mb-8">
        <div className="inline-block px-4 py-1.5 bg-white/80 border border-[#E5DDD3] rounded-full mb-4">
          <span className="text-xs font-bold text-[#A47C4B] uppercase tracking-wider">
            시작하기
          </span>
        </div>
        <h2 className="text-3xl font-black text-[#2C2419] mb-2 font-title italic">
          오늘 어땠어?<br />짧게라도 괜찮아
        </h2>
        <p className="text-sm text-[#5A4A3A] font-diary leading-relaxed">
          3줄도 충분해. 매일 쌓이면 이음이가 함께 정리해줄게.
        </p>
      </div>

      {/* 닉네임 입력 */}
      <div className="mb-6">
        <label className="block text-sm font-medium text-[#5A4A3A] mb-2">
          닉네임
        </label>
        <input
          type="text"
          value={nickname}
          onChange={(e) => setNickname(e.target.value)}
          className="w-full px-4 py-3 border border-[#E5DDD3] rounded-full focus:outline-none focus:ring-2 focus:ring-[#A47C4B] focus:border-[#A47C4B]"
          placeholder="예: 아리아"
        />
      </div>

      {/* 일일 목표 입력 */}
      <div className="mb-6">
        <label className="block text-sm font-medium text-[#5A4A3A] mb-2">
          일일 목표
        </label>
        <input
          type="text"
          value={dailyGoal}
          onChange={(e) => setDailyGoal(e.target.value)}
          className="w-full px-4 py-3 border border-[#E5DDD3] rounded-full focus:outline-none focus:ring-2 focus:ring-[#A47C4B] focus:border-[#A47C4B]"
          placeholder="예: 하루를 돌아보기"
        />
      </div>

      {/* 피드백 */}
      <div className="text-center">
        {nickname.trim().length > 0 ? (
          <div className="card-elevated inline-block px-6 py-3">
            <p className="text-sm font-semibold text-[#2C2419]">
              <span className="text-gradient-gold">{nickname}</span> 님의 정보가 저장되었습니다
            </p>
          </div>
        ) : (
          <div className="bg-[#FFE4A3]/20 border-2 border-[#D4A574]/30 rounded-[1.5rem] px-6 py-3 inline-block">
            <p className="text-xs text-[#8B7A6A] font-semibold">
              ⚠️ 닉네임을 입력해주세요
            </p>
          </div>
        )}
      </div>
    </div>
  );
}