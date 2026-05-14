import React, { useState, useMemo, useEffect, useRef } from 'react';
import { 
  format, 
  subDays, 
  startOfMonth, 
  endOfMonth, 
  startOfWeek, 
  endOfWeek, 
  eachDayOfInterval, 
  isSameMonth, 
  isSameDay, 
  addMonths, 
  subMonths,
  isWithinInterval
} from 'date-fns';
import { ko } from 'date-fns/locale';
import {
  ChevronLeft,
  ChevronRight,
  Smile,
  Frown,
  Meh,
  Angry,
  Heart,
  CloudRain,
  Sun,
  Moon,
  Trash2,
  Edit3,
  List,
  BarChart2,
  Sparkles,
  Calendar as CalendarIcon,
  Camera,
  Gamepad2,
  Zap,
  TrendingUp,
  BrainCircuit,
  Loader2,
  Target,
  Send,
  MessageCircle,
  RotateCcw,
  Check,
  Smartphone,
  Trophy
} from 'lucide-react';

const apiKey = ""; // API Key provided by environment

// 고품격 마스코트 이미지
const DEFAULT_MASCOT = 'https://images.unsplash.com/photo-1513245535761-07750ee135e7?q=80&w=400&auto=format&fit=crop';

const EMOTIONS = [
  { id: 'happy', icon: Smile, label: '환희의 순간', color: 'text-amber-500', bg: 'bg-amber-50/50', border: 'border-amber-100', gradient: 'from-amber-50 to-orange-50' },
  { id: 'sad', icon: Frown, label: '비의 선율', color: 'text-blue-500', bg: 'bg-blue-50/50', border: 'border-blue-100', gradient: 'from-blue-50 to-indigo-50' },
  { id: 'meh', icon: Meh, label: '정적의 시간', color: 'text-stone-400', bg: 'bg-stone-50/50', border: 'border-stone-100', gradient: 'from-stone-50 to-zinc-50' },
  { id: 'angry', icon: Angry, label: '뜨거운 열정', color: 'text-rose-500', bg: 'bg-rose-50/50', border: 'border-rose-100', gradient: 'from-rose-50 to-red-50' },
  { id: 'loved', icon: Heart, label: '사랑의 온기', color: 'text-pink-400', bg: 'bg-pink-50/50', border: 'border-pink-100', gradient: 'from-pink-50 to-purple-50' },
  { id: 'gloomy', icon: CloudRain, label: '안개의 사색', color: 'text-indigo-400', bg: 'bg-indigo-50/50', border: 'border-indigo-100', gradient: 'from-indigo-50 to-slate-100' },
  { id: 'energetic', icon: Sun, label: '태양의 활력', color: 'text-orange-400', bg: 'bg-orange-50/50', border: 'border-orange-100', gradient: 'from-orange-50 to-yellow-50' },
  { id: 'calm', icon: Moon, label: '달빛의 안식', color: 'text-violet-500', bg: 'bg-violet-50/50', border: 'border-violet-100', gradient: 'from-violet-50 to-slate-100' },
];

const App = () => {
  const [view, setView] = useState('LIST'); 
  const [currentMonth, setCurrentMonth] = useState(new Date());
  const [diaries, setDiaries] = useState([
    { id: 1, date: new Date(), emotion: 'calm', content: '오늘도 고요한 정적 속에서 하루를 잘 마무리했습니다. 집사의 차 한 잔이 참 따뜻했네요.' },
    { id: 2, date: subDays(new Date(), 1), emotion: 'happy', content: '예상치 못한 작은 성취가 큰 기쁨으로 다가온 날이었습니다. 이 기분을 소중히 간직해야겠어요.' },
  ]);
  
  const [mascotImg, setMascotImg] = useState(DEFAULT_MASCOT);
  const [streak, setStreak] = useState(2);
  const [churuCount, setChuruCount] = useState(12);
  const [toyCount, setToyCount] = useState(4);
  const [happiness, setHappiness] = useState(85);
  const [isInteracting, setIsInteracting] = useState(false);
  const [interactionMsg, setInteractionMsg] = useState("");

  const [currentDiary, setCurrentDiary] = useState(null);
  const [editEmotion, setEditEmotion] = useState(null);
  const [editText, setEditText] = useState('');
  const [filterEmotion, setFilterEmotion] = useState('all');

  const [aiAnalysis, setAiAnalysis] = useState(null);
  const [isAiLoading, setIsAiLoading] = useState(false);
  const [chatStep, setChatStep] = useState('IDLE'); 
  const [chatInput, setChatInput] = useState('');
  const scrollRef = useRef(null);

  useEffect(() => {
    if (scrollRef.current) scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
  }, [chatStep, interactionMsg, aiAnalysis]);

  const handleImageUpload = (e) => {
    const file = e.target.files[0];
    if (file) {
      const reader = new FileReader();
      reader.onloadend = () => setMascotImg(reader.result);
      reader.readAsDataURL(file);
    }
  };

  const currentTheme = useMemo(() => {
    if (view === 'CREATE' || view === 'INTERACT') return 'from-[#fdfbf7] to-[#f5f0e6]';
    if (view === 'DETAIL' && currentDiary) return EMOTIONS.find(e => e.id === currentDiary.emotion)?.gradient || 'from-[#faf9f6] to-white';
    return 'from-[#faf9f6] to-white';
  }, [view, currentDiary]);

  const callGeminiAPI = async (payload, endpoint = 'generateContent') => {
    const delays = [1000, 2000, 4000, 8000, 16000];
    for (let i = 0; i < delays.length; i++) {
      try {
        const response = await fetch(`https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash-preview-09-2025:${endpoint}?key=${apiKey}`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(payload)
        });
        if (!response.ok) throw new Error('API Error');
        return await response.json();
      } catch (error) {
        if (i === delays.length - 1) throw error;
        await new Promise(res => setTimeout(res, delays[i]));
      }
    }
  };

  const analyzeChatAndCreateDiary = async () => {
    if (!chatInput.trim()) return;
    setChatStep('ANALYZING');
    const prompt = `당신은 고풍스러운 저택의 수석 바텐더 고양이 집사입니다. 주인님이 말씀하신 오늘의 하루를 분석해서 정보를 추출하세요. 
    말투는 매우 정중한 극존칭이며 고양이 특유의 어조(~냥, ~옹)를 섞으세요.
    주인님의 대화: "${chatInput}"
    반드시 다음 JSON 형식으로만 답변하세요:
    {
      "emotion": "happy, sad, meh, angry, loved, gloomy, energetic, calm 중 하나",
      "content": "주인님의 대화를 바탕으로 작성한 정중하고 품격 있는 3-4문장의 일기 내용"
    }`;
    try {
      const result = await callGeminiAPI({
        contents: [{ parts: [{ text: prompt }] }],
        generationConfig: { responseMimeType: "application/json" }
      });
      const parsed = JSON.parse(result.candidates?.[0]?.content?.parts?.[0]?.text);
      setEditEmotion(parsed.emotion);
      setEditText(parsed.content);
      setChatStep('CONFIRMING');
    } catch (error) {
      setChatStep('CHATTING');
      setInteractionMsg("송구하옵니다 주인님, 다시 한번 들려주시겠습니까?");
    }
  };

  const fetchAIAnalysis = async (type) => {
    setIsAiLoading(true);
    setAiAnalysis(null);
    const targetDiaries = type === 'weekly' 
      ? diaries.filter(d => isWithinInterval(d.date, { start: subDays(new Date(), 7), end: new Date() }))
      : diaries.filter(d => isSameMonth(d.date, currentMonth));
    if (targetDiaries.length === 0) {
      setAiAnalysis("주인님, 분석해 드릴 기록이 아직 준비되지 않았습니다냥.");
      setIsAiLoading(false);
      return;
    }
    const diarySummary = targetDiaries.map(d => `[${format(d.date, 'yyyy-MM-dd')}] 감정: ${EMOTIONS.find(e => e.id === d.emotion)?.label}, 내용: ${d.content}`).join('\n');
    const prompt = `고풍스러운 바텐더 집사로서 주인님의 ${type === 'weekly' ? '주간' : '월간'} 리포트를 작성하세요. [오늘의 빈티지 요약], [소믈리에의 마음 처방], [미래의 성취를 위한 목표] 순서로 아주 정중하게 작성하세요.\n${diarySummary}`;
    try {
      const result = await callGeminiAPI({ contents: [{ parts: [{ text: prompt }] }] });
      setAiAnalysis(result.candidates?.[0]?.content?.parts?.[0]?.text);
    } catch (error) { setAiAnalysis("송구하옵니다 주인님, 오류가 발생했습니다냥."); }
    finally { setIsAiLoading(false); }
  };

  const handleSave = () => {
    if (!editEmotion || !editText.trim()) return;
    setDiaries([{ id: Date.now(), date: new Date(), emotion: editEmotion, content: editText }, ...diaries]);
    setStreak(prev => prev + 1);
    setChuruCount(prev => prev + 1);
    setView('LIST');
    resetForm();
  };

  const resetForm = () => { setEditEmotion(null); setEditText(''); setChatStep('IDLE'); setChatInput(''); };

  const interactWithButler = (type) => {
    if (type === 'churu' && churuCount > 0) {
      setChuruCount(prev => prev - 1);
      setHappiness(prev => Math.min(100, prev + 8));
      setInteractionMsg("주인님께서 하사하신 츄르, 정말 감격스럽습니다냥.");
    } else if (type === 'toy' && toyCount > 0) {
      setToyCount(prev => prev - 1);
      setHappiness(prev => Math.min(100, prev + 5));
      setInteractionMsg("사냥은 언제나 즐겁군요! 주인님 최고입니다냥.");
    } else return;
    setIsInteracting(true);
    setTimeout(() => { setIsInteracting(false); setInteractionMsg(""); }, 3500);
  };

  const handleDateClick = (day) => {
    const foundDiary = diaries.find(d => isSameDay(d.date, day));
    if (foundDiary) { setCurrentDiary(foundDiary); setView('DETAIL'); }
    else if (isSameDay(day, new Date())) { setView('CREATE'); setChatStep('IDLE'); }
  };

  const statsData = useMemo(() => {
    const currentMonthDiaries = diaries.filter(d => isSameMonth(d.date, currentMonth));
    const counts = EMOTIONS.map(e => ({
      ...e,
      count: currentMonthDiaries.filter(d => d.emotion === e.id).length
    })).sort((a, b) => b.count - a.count);
    const topEmotion = counts.length > 0 && counts[0].count > 0 ? counts[0] : null;
    return { counts, total: currentMonthDiaries.length, topEmotion };
  }, [diaries, currentMonth]);

  const calendarDays = useMemo(() => {
    const start = startOfWeek(startOfMonth(currentMonth));
    const end = endOfWeek(endOfMonth(currentMonth));
    return eachDayOfInterval({ start, end });
  }, [currentMonth]);

  return (
    <div className={`min-h-screen bg-[#f3f0e9] flex justify-center items-center p-0 md:p-8 font-main antialiased overflow-hidden`}>
      <div className={`w-full max-w-md h-screen md:h-[840px] bg-gradient-to-br ${currentTheme} relative md:rounded-[3rem] shadow-[0_40px_80px_-20px_rgba(0,0,0,0.1)] overflow-hidden flex flex-col transition-all duration-1000 border-2 border-white`}>
        
        {/* 상태바 (사이즈 축소) */}
        <div className="h-10 w-full flex justify-between items-center px-8 text-[9px] font-black text-stone-400 tracking-widest pt-3 z-20 pointer-events-none font-sans uppercase">
          <span>{format(new Date(), 'HH:mm')}</span>
          <div className="flex items-center space-x-2">
            <Smartphone size={12} className="opacity-20" />
          </div>
        </div>

        {/* 헤더 바 (사이즈 축소) */}
        <header className="p-6 pb-2 flex justify-between items-center z-10">
          <div className="flex items-center space-x-3">
            <label className="relative cursor-pointer group">
              <img src={mascotImg} alt="Mascot" className="w-11 h-11 rounded-[1.2rem] object-cover border border-white shadow-md" />
              <input type="file" className="hidden" onChange={handleImageUpload} accept="image/*" />
            </label>
            <div>
              <div className="flex items-center space-x-1 text-[8px] font-black text-amber-600/70 uppercase tracking-widest font-sans">
                <Zap size={8} className="fill-amber-500 text-amber-500" /> 
                <span>STREAK {streak}D</span>
              </div>
              <h1 className="text-sm font-black text-stone-800 font-title tracking-tight italic">Tamanya</h1>
            </div>
          </div>
          <div className="bg-white/90 px-3 py-1.5 rounded-full flex items-center space-x-1 shadow-sm border border-stone-100 font-sans">
            <span className="text-xs">🍬</span>
            <span className="text-[10px] font-black text-stone-600">{churuCount}</span>
          </div>
        </header>

        <main className="flex-1 p-5 overflow-y-auto custom-scrollbar relative" ref={scrollRef}>
          
          {view === 'LIST' && (
            <div className="space-y-6 animate-in fade-in duration-700 pb-20 px-1">
              {/* 마중 카드 (폰트 및 여백 축소) */}
              <div 
                onClick={() => { setView('CREATE'); setChatStep('CHATTING'); }}
                className="bg-white/80 p-6 rounded-[2.5rem] border border-white flex items-center space-x-4 cursor-pointer hover:bg-white transition-all shadow-sm"
              >
                <div className="relative">
                  <img src={mascotImg} alt="Butler" className="w-16 h-16 rounded-[1.6rem] object-cover shadow-sm" />
                  <div className="absolute -bottom-1 -right-1 bg-green-400 w-3.5 h-3.5 rounded-full border-2 border-white animate-pulse"></div>
                </div>
                <div className="flex-1">
                  <h3 className="text-base font-bold text-stone-800 leading-tight italic font-diary">
                    "주인님, 오늘 이야기를<br/>기록해 드릴까요?"
                  </h3>
                </div>
                <ChevronRight size={18} className="text-stone-300" />
              </div>

              <div className="flex justify-between items-center px-2">
                <h2 className="text-[9px] font-black text-stone-300 tracking-[0.2em] uppercase font-sans">Mood Archives</h2>
                <select value={filterEmotion} onChange={(e) => setFilterEmotion(e.target.value)} className="text-[9px] font-bold bg-white/40 border-none rounded-lg px-3 py-1.5 shadow-sm outline-none font-main">
                  <option value="all">ALL BLENDS</option>
                  {EMOTIONS.map(e => <option key={e.id} value={e.id}>{e.label.toUpperCase()}</option>)}
                </select>
              </div>

              <div className="grid gap-4">
                {diaries.filter(d => filterEmotion === 'all' || d.emotion === filterEmotion).map((diary) => {
                  const emotion = EMOTIONS.find(e => e.id === diary.emotion);
                  return (
                    <div key={diary.id} onClick={() => { setCurrentDiary(diary); setView('DETAIL'); }} className="bg-white/70 p-5 rounded-[2rem] shadow-sm hover:shadow-md border border-white transition-all cursor-pointer flex items-center space-x-4">
                      <div className={`p-4 rounded-[1.4rem] ${emotion.bg}`}><emotion.icon className={emotion.color} size={24} /></div>
                      <div className="flex-1 overflow-hidden">
                        <span className="text-[9px] font-bold text-stone-300 uppercase tracking-widest font-sans">{format(diary.date, 'MMM dd, EEEE', { locale: ko })}</span>
                        <p className="text-stone-700 font-semibold truncate mt-1 font-diary text-base tracking-tight">{diary.content}</p>
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          )}

          {view === 'CREATE' && (
            <div className="space-y-6 h-full flex flex-col animate-in zoom-in-95 duration-500 pb-20">
              {chatStep === 'IDLE' && (
                <div className="flex-1 flex flex-col items-center justify-center text-center space-y-6 px-4">
                  <div className="relative">
                    <img src={mascotImg} alt="Butler" className="w-36 h-36 rounded-[3.5rem] object-cover shadow-xl border-4 border-white relative" />
                  </div>
                  <div className="space-y-2">
                    <h2 className="text-2xl font-black text-stone-800 italic tracking-tighter font-title">"기분을 브루잉할까요?"</h2>
                    <p className="text-xs text-stone-400 max-w-[200px] mx-auto font-main leading-relaxed">바텐더 집사가 가장 고결한 문장으로<br/>주인님의 하루를 기록합니다냥.</p>
                  </div>
                  <button onClick={() => setChatStep('CHATTING')} className="px-10 py-5 bg-stone-900 text-amber-50 rounded-[2rem] font-black shadow-xl hover:scale-105 transition-all font-main uppercase text-[10px] tracking-widest">대화 시작하기</button>
                  <button onClick={() => setView('LIST')} className="text-stone-300 font-bold text-[9px] uppercase tracking-[0.2em] font-sans">Return</button>
                </div>
              )}

              {chatStep !== 'IDLE' && (
                <div className="flex-1 flex flex-col space-y-5 pt-4">
                  <div className="flex items-start space-x-3">
                    <img src={mascotImg} alt="Butler" className="w-10 h-10 rounded-xl object-cover border border-white" />
                    <div className="bg-stone-900 p-5 rounded-[2rem] rounded-tl-none shadow-xl text-[12px] font-medium text-amber-50/90 max-w-[85%] leading-relaxed italic font-diary">
                      {chatStep === 'CHATTING' ? '"주인님, 어서오십시오. 오늘의 기분은 어떤 향기로 기억될까요? 편히 들려주시지요냥."' : 
                       chatStep === 'ANALYZING' ? '"이야기를 정성껏 숙성 중입니다냥..."' : 
                       '"주인님의 하루를 이렇게 블렌딩해 보았습니다냥. 마음에 드시는지요?"'}
                    </div>
                  </div>

                  {chatStep === 'CONFIRMING' && (
                    <div className="animate-in slide-in-from-bottom-8 duration-700 space-y-5 pb-20">
                      <div className="flex flex-col items-center">
                        <div className={`p-8 rounded-[2.5rem] ${EMOTIONS.find(e => e.id === editEmotion)?.bg} shadow-lg mb-3`}>
                          {(() => { const e = EMOTIONS.find(e => e.id === editEmotion); return e ? <e.icon size={50} className={e.color} /> : <Meh size={50}/>; })()}
                        </div>
                        <p className="text-[9px] font-black text-stone-400 uppercase tracking-widest font-sans">{EMOTIONS.find(e => e.id === editEmotion)?.label}</p>
                      </div>
                      <div className="bg-white/95 p-8 rounded-[3rem] shadow-sm text-base italic text-stone-800 leading-relaxed border border-[#eee8dc] font-diary text-center">
                        "{editText}"
                      </div>
                      <div className="flex space-x-3">
                        <button onClick={() => { setChatStep('CHATTING'); setEditText(''); setEditEmotion(null); }} className="flex-1 py-4 bg-stone-50 text-stone-400 rounded-[1.5rem] font-bold text-[9px] uppercase tracking-widest">Retry</button>
                        <button onClick={handleSave} className="flex-1 py-4 bg-stone-900 text-amber-100 rounded-[1.5rem] font-bold text-[9px] uppercase shadow-lg">Archive</button>
                      </div>
                    </div>
                  )}

                  <div className="flex-1" />
                  {chatStep === 'CHATTING' && (
                    <div className="bg-white p-2 rounded-full shadow-lg flex items-center space-x-2 border border-stone-50 mb-6">
                      <input autoFocus value={chatInput} onChange={(e) => setChatInput(e.target.value)} onKeyPress={(e) => e.key === 'Enter' && analyzeChatAndCreateDiary()} placeholder="이야기를 들려주세요..." className="flex-1 px-5 py-3 outline-none text-stone-800 font-diary text-sm placeholder:text-stone-300" />
                      <button onClick={analyzeChatAndCreateDiary} disabled={!chatInput.trim()} className="p-4 bg-stone-900 text-white rounded-full transition-all"><Send size={18} /></button>
                    </div>
                  )}
                </div>
              )}
            </div>
          )}

          {view === 'INTERACT' && (
            <div className="space-y-10 animate-in zoom-in-95 duration-700 text-center flex flex-col items-center pt-8 pb-24">
              <div className="space-y-1">
                <h2 className="text-2xl font-black text-stone-900 italic tracking-tighter font-title">Private Lounge</h2>
                <p className="text-[10px] text-stone-400 font-bold uppercase tracking-[0.2em] font-sans">At your service</p>
              </div>
              <div className="relative mt-8">
                <div className={`w-60 h-60 rounded-[4.5rem] bg-white border-8 border-white shadow-2xl overflow-hidden transition-all duration-1000 ${isInteracting ? 'scale-105 rotate-1' : ''}`}>
                  <img src={mascotImg} alt="Butler" className="w-full h-full object-cover" />
                </div>
                {interactionMsg && (
                   <div className="absolute -top-12 left-1/2 -translate-x-1/2 bg-stone-900 text-amber-50 px-8 py-4 rounded-[1.8rem] text-[11px] font-medium shadow-2xl animate-bounce-slow whitespace-nowrap z-20 italic font-diary">
                      {interactionMsg}
                      <div className="absolute bottom-[-6px] left-1/2 -translate-x-1/2 w-3 h-3 bg-stone-900 rotate-45"></div>
                   </div>
                )}
                <div className="mt-10 bg-white/60 p-3 rounded-full w-52 mx-auto border border-white/40">
                  <div className="flex justify-between items-center mb-1.5 px-3">
                    <span className="text-[8px] font-black text-stone-300 uppercase tracking-widest">Loyalty</span>
                    <span className="text-[9px] font-black text-amber-600">{happiness}%</span>
                  </div>
                  <div className="w-full h-2 bg-stone-100/50 rounded-full overflow-hidden">
                    <div className="h-full bg-amber-500 transition-all duration-1000" style={{ width: `${happiness}%` }}></div>
                  </div>
                </div>
              </div>
              <div className="grid grid-cols-2 gap-5 w-full mt-6 px-2">
                <button onClick={() => interactWithButler('churu')} className="bg-white/90 p-6 rounded-[2.5rem] shadow-sm hover:shadow-md transition-all flex flex-col items-center border border-white disabled:opacity-30">
                  <span className="text-3xl mb-2">🍷</span>
                  <span className="text-[9px] font-black uppercase text-slate-400 tracking-widest">Vintage {churuCount}</span>
                </button>
                <button onClick={() => interactWithButler('toy')} className="bg-white/90 p-6 rounded-[2.5rem] shadow-sm hover:shadow-md transition-all flex flex-col items-center border border-white disabled:opacity-30">
                  <span className="text-3xl mb-2">🧶</span>
                  <span className="text-[9px] font-black uppercase text-slate-400 tracking-widest">Leisure {toyCount}</span>
                </button>
              </div>
            </div>
          )}

          {view === 'STATS' && (
            <div className="space-y-6 animate-in slide-in-from-right-4 duration-700 px-1 pb-24 pt-4">
              <header className="mb-6 pl-2 border-l-4 border-amber-400"><h2 className="text-3xl font-black text-stone-900 italic tracking-tighter font-title">Reports</h2></header>
              <div className="grid grid-cols-2 gap-4 mb-6">
                <button onClick={() => fetchAIAnalysis('weekly')} className="bg-white p-5 rounded-[2.2rem] shadow-sm flex flex-col items-center justify-center hover:bg-stone-50 transition-all font-main group"><BrainCircuit className="text-amber-500 mb-2" size={24} /><span className="text-[9px] font-black uppercase tracking-[0.1em] text-stone-400">WEEKLY</span></button>
                <button onClick={() => fetchAIAnalysis('monthly')} className="bg-white p-5 rounded-[2.2rem] shadow-sm flex flex-col items-center justify-center hover:bg-stone-50 transition-all font-main group"><TrendingUp className="text-indigo-400 mb-2" size={24} /><span className="text-[9px] font-black uppercase tracking-[0.1em] text-stone-400">MONTHLY</span></button>
              </div>
              
              <div className="grid grid-cols-2 gap-3 mb-4 font-sans">
                <div className="bg-white/90 p-4 rounded-[1.8rem] shadow-sm flex flex-col items-center border border-white">
                   <Target className="text-stone-200 mb-1" size={20} />
                   <span className="text-lg font-black text-stone-800">{statsData.total}</span>
                </div>
                <div className="bg-white/90 p-4 rounded-[1.8rem] shadow-sm flex flex-col items-center border border-white">
                   <Trophy className="text-amber-400 mb-1" size={20} />
                   <span className="text-lg font-black text-stone-800">{streak}D</span>
                </div>
              </div>

              {(isAiLoading || aiAnalysis) && (
                <div className="bg-stone-900 p-10 rounded-[3.5rem] shadow-xl text-[13px] italic leading-relaxed whitespace-pre-wrap relative overflow-hidden animate-in zoom-in-95 duration-700 font-diary text-amber-50/80">
                  {isAiLoading ? <div className="flex flex-col items-center py-8 space-y-4"><Loader2 className="text-amber-500 animate-spin" size={32} /><p className="text-[9px] font-black tracking-widest animate-pulse uppercase">Brewing...</p></div> : aiAnalysis}
                </div>
              )}
            </div>
          )}

          {view === 'CALENDAR' && (
            <div className="space-y-8 animate-in fade-in duration-700 pt-4 px-1 pb-24">
              <header className="flex justify-between items-center mb-6 px-2">
                <button onClick={() => setCurrentMonth(subMonths(currentMonth, 1))} className="p-3.5 bg-white rounded-[1.2rem] text-stone-300 shadow-md transition-all hover:text-amber-500"><ChevronLeft size={18}/></button>
                <h2 className="text-2xl font-black text-stone-900 italic tracking-tighter font-title">{format(currentMonth, 'MMMM yyyy')}</h2>
                <button onClick={() => setCurrentMonth(addMonths(currentMonth, 1))} className="p-3.5 bg-white rounded-[1.2rem] text-stone-300 shadow-md transition-all hover:text-amber-500"><ChevronRight size={18}/></button>
              </header>
              <div className="bg-white rounded-[3.5rem] p-8 border border-white shadow-lg overflow-hidden">
                <div className="grid grid-cols-7 mb-8 text-[9px] font-black opacity-30 font-sans tracking-widest uppercase">
                  {['S', 'M', 'T', 'W', 'T', 'F', 'S'].map((day, i) => (
                    <div key={`${day}-${i}`} className={`text-center ${i === 0 ? 'text-rose-500' : i === 6 ? 'text-indigo-500' : 'text-stone-900'}`}>{day}</div>
                  ))}
                </div>
                <div className="grid grid-cols-7 gap-y-6 font-sans">{calendarDays.map((day, idx) => {
                  const diary = diaries.find(d => isSameDay(d.date, day));
                  const emotion = diary ? EMOTIONS.find(e => e.id === diary.emotion) : null;
                  const isToday = isSameDay(day, new Date());
                  const isOtherMonth = !isSameMonth(day, currentMonth);
                  return (
                    <div key={idx} onClick={() => handleDateClick(day)} className={`aspect-square flex flex-col items-center justify-center relative cursor-pointer group transition-all rounded-[1.4rem] ${isOtherMonth ? 'opacity-10' : 'opacity-100'}`}>
                      <span className={`text-[11px] font-black mb-1.5 ${isToday ? 'text-amber-600' : 'text-stone-400'}`}>{format(day, 'd')}</span>
                      {emotion ? (
                        <div className={`p-1.5 rounded-xl ${emotion.bg} shadow-sm transition-transform`}><emotion.icon size={16} className={emotion.color} /></div>
                      ) : (
                        <div className={`w-1.5 h-1.5 bg-stone-100 rounded-full mt-1 ${isToday && 'bg-amber-400'}`}></div>
                      )}
                    </div>
                  );
                })}</div>
              </div>
            </div>
          )}

          {view === 'DETAIL' && (
            <div className="space-y-10 animate-in slide-in-from-right-12 duration-1000 px-1 pb-24 pt-4">
              <div className="flex justify-between items-center"><button onClick={() => setView('LIST')} className="p-3.5 bg-white hover:bg-stone-50 rounded-[1.5rem] transition-all text-stone-300 shadow-lg border border-white"><ChevronLeft size={20}/></button><button onClick={() => { setDiaries(diaries.filter(d => d.id !== currentDiary.id)); setView('LIST'); }} className="p-3.5 bg-rose-50 text-rose-300 rounded-[1.5rem] shadow-lg hover:text-rose-500 transition-all border border-white"><Trash2 size={20}/></button></div>
              <div className="text-center space-y-6 pt-4">
                <div className={`inline-block p-12 rounded-[4rem] ${EMOTIONS.find(e => e.id === currentDiary.emotion)?.bg || 'bg-white'} mb-1 shadow-2xl relative ring-[8px] ring-white`}>
                   <div className="absolute inset-0 bg-white/40 blur-[30px] rounded-full" />
                   {(() => { const e = EMOTIONS.find(e => e.id === currentDiary.emotion); return e ? <e.icon size={80} className={`${e.color} relative z-10`} /> : <Meh size={80} />; })()}
                </div>
                <div className="space-y-1">
                   <h3 className="text-3xl font-black text-stone-900 italic tracking-tighter font-title leading-tight">{format(currentDiary.date, 'yyyy. MM. dd')}</h3>
                   <p className="text-[9px] font-black text-stone-300 uppercase tracking-[0.4em] font-sans ml-1">{EMOTIONS.find(e => e.id === currentDiary.emotion)?.label || '기록'}</p>
                </div>
              </div>
              <div className="bg-white/95 p-10 rounded-[4.5rem] min-h-[350px] text-stone-800 leading-[2.1] shadow-xl border-2 border-white text-xl italic font-medium font-diary text-center">
                "{currentDiary.content}"
              </div>
            </div>
          )}

          {/* 마중 플로팅 (사이즈 축소) */}
          {(view === 'LIST' || view === 'CALENDAR' || view === 'STATS') && (
            <div className="fixed bottom-32 right-8 flex flex-col items-end z-30 pointer-events-none">
               <div className="bg-stone-900 px-5 py-2.5 rounded-[1.4rem] shadow-xl border border-stone-800 text-[9px] font-black text-amber-50 mb-4 animate-bounce-slow tracking-widest uppercase italic font-sans">
                 I'm waiting Master 🐾
               </div>
               <button 
                onClick={() => { setView('CREATE'); setChatStep('IDLE'); }}
                className="w-20 h-20 rounded-[3rem] overflow-hidden border-[4px] border-white shadow-2xl hover:scale-110 active:scale-95 transition-all group p-1 bg-white pointer-events-auto"
               >
                 <img src={mascotImg} alt="Butler" className="w-full h-full rounded-[2.6rem] object-cover transition-all" />
               </button>
            </div>
          )}
        </main>

        {/* 내비게이션 (사이즈 축소) */}
        <nav className="h-28 bg-white/95 backdrop-blur-3xl border-t border-stone-100 flex justify-around items-center px-10 rounded-b-[3rem] md:rounded-b-[3rem] z-40 shadow-[0_-10px_30px_rgba(0,0,0,0.01)] pb-6 font-sans">
          <button onClick={() => setView('LIST')} className={`p-4 transition-all duration-500 rounded-[1.8rem] ${view === 'LIST' ? 'bg-stone-900 text-amber-400 shadow-xl' : 'text-stone-200 hover:text-stone-400'}`}><List size={22} /></button>
          <button onClick={() => setView('CALENDAR')} className={`p-4 transition-all duration-500 rounded-[1.8rem] ${view === 'CALENDAR' ? 'bg-stone-900 text-amber-400 shadow-xl' : 'text-stone-200 hover:text-stone-400'}`}><CalendarIcon size={22} /></button>
          <button onClick={() => setView('INTERACT')} className={`p-4 transition-all duration-500 rounded-[1.8rem] ${view === 'INTERACT' ? 'bg-stone-900 text-amber-400 shadow-xl' : 'text-stone-200 hover:text-stone-400'}`}><Gamepad2 size={22} /></button>
          <button onClick={() => { setView('STATS'); setAiAnalysis(null); }} className={`p-4 transition-all duration-500 rounded-[1.8rem] ${view === 'STATS' ? 'bg-stone-900 text-amber-400 shadow-xl' : 'text-stone-200 hover:text-stone-400'}`}><BarChart2 size={22} /></button>
        </nav>
      </div>

      <style>
        {`
        @import url('https://fonts.googleapis.com/css2?family=Gowun+Batang:wght@400;700&family=Gowun+Dodum&family=Playfair+Display:ital,wght@0,400;0,900;1,400;1,900&display=swap');
        
        .font-main { font-family: 'Gowun Dodum', sans-serif; }
        .font-diary { font-family: 'Gowun Batang', serif; }
        .font-title { font-family: 'Playfair Display', serif; }
        .font-sans { font-family: ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif; }

        body, div, p, span, h1, h2, h3, button, input, textarea {
          font-family: 'Gowun Dodum', sans-serif;
          letter-spacing: -0.03em;
        }

        @keyframes bounce-slow { 0%, 100% { transform: translateY(0); } 50% { transform: translateY(-10px); } }
        .animate-bounce-slow { animation: bounce-slow 3s ease-in-out infinite; }
        
        .custom-scrollbar::-webkit-scrollbar { width: 0px; }
        .custom-scrollbar { scrollbar-width: none; -ms-overflow-style: none; }
        `}
      </style>
    </div>
  );
};

export default App;