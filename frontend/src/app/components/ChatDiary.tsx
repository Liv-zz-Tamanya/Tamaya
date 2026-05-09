import { useState, useRef, useEffect } from 'react';
import { Send, Mic, MicOff, Volume2, VolumeX, Check } from 'lucide-react';
import { chatApi, diaryApi, voiceApi, ChatSessionResponse, ChatMessage as ApiChatMessage } from '../utils/api';
import { EMOTIONS } from '../utils/mockData';
import { updateProgressOnDiary } from '../utils/rewardSystem';
import { EumiCharacter } from './EumiCharacter';

interface ChatDiaryProps {
  onComplete: () => void;
}

export function ChatDiary({ onComplete }: ChatDiaryProps) {
  const [session, setSession] = useState<ChatSessionResponse | null>(null);
  const [input, setInput] = useState('');
  const [isRecording, setIsRecording] = useState(false);
  const [isTTSEnabled, setIsTTSEnabled] = useState(true);
  const [isSending, setIsSending] = useState(false);
  const [selectedEmotion, setSelectedEmotion] = useState<string>('');
  const [satisfaction, setSatisfaction] = useState(50);
  const [showEmotionSelect, setShowEmotionSelect] = useState(false);
  const [isCompleting, setIsCompleting] = useState(false);
  
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const audioChunksRef = useRef<Blob[]>([]);

  // 세션 시작
  useEffect(() => {
    initSession();
  }, []);

  // 자동 스크롤
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [session?.messages]);

  const initSession = async () => {
    try {
      const newSession = await chatApi.startSession();
      setSession(newSession);
      
      // 첫 메시지 TTS
      if (newSession.messages.length > 0) {
        playTTS(newSession.messages[0].content);
      }
    } catch (error) {
      console.error('Failed to start session:', error);
    }
  };

  // TTS 재생
  const playTTS = async (text: string) => {
    if (!isTTSEnabled) return;
    
    try {
      const audioBlob = await voiceApi.textToSpeech(text);
      const audioUrl = URL.createObjectURL(audioBlob);
      const audio = new Audio(audioUrl);
      audio.play();
    } catch (error) {
      console.error('TTS error:', error);
    }
  };

  // 메시지 전송
  const handleSend = async () => {
    if (!input.trim() || !session || isSending) return;

    setIsSending(true);

    try {
      const response = await chatApi.sendMessage(session.id, input.trim());
      
      // 세션 업데이트
      const updatedSession = await chatApi.getSession(session.id);
      setSession(updatedSession);
      
      setInput('');
      
      // AI 응답 TTS
      playTTS(response.ai_message.content);
      
      // 5회 이상 대화 시 감정 선택 제안
      if (response.should_suggest_finalize && !showEmotionSelect) {
        setTimeout(() => {
          setShowEmotionSelect(true);
        }, 1000);
      }
    } catch (error) {
      console.error('Failed to send message:', error);
    } finally {
      setIsSending(false);
    }
  };

  // 음성 녹음 시작
  const startRecording = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const mediaRecorder = new MediaRecorder(stream);
      mediaRecorderRef.current = mediaRecorder;
      audioChunksRef.current = [];

      mediaRecorder.ondataavailable = (event) => {
        if (event.data.size > 0) {
          audioChunksRef.current.push(event.data);
        }
      };

      mediaRecorder.onstop = async () => {
        const audioBlob = new Blob(audioChunksRef.current, { type: 'audio/webm' });
        
        try {
          const text = await voiceApi.speechToText(audioBlob);
          setInput(text);
        } catch (error) {
          console.error('STT error:', error);
        }
        
        stream.getTracks().forEach(track => track.stop());
      };

      mediaRecorder.start();
      setIsRecording(true);
    } catch (error) {
      console.error('Failed to start recording:', error);
      alert('마이크 권한을 허용해주세요.');
    }
  };

  // 음성 녹음 중지
  const stopRecording = () => {
    if (mediaRecorderRef.current && isRecording) {
      mediaRecorderRef.current.stop();
      setIsRecording(false);
    }
  };

  // 일기 완성
  const handleComplete = async () => {
    if (!session || !selectedEmotion) {
      alert('감정을 선택해주세요!');
      return;
    }

    setIsCompleting(true);

    try {
      // 1. 일기 생성 (백엔드가 자동으로 대화 내용 요약)
      const diary = await diaryApi.finalize(session.id);
      
      // 2. 보상 시스템 업데이트
      updateProgressOnDiary();
      
      // 3. 완료
      onComplete();
    } catch (error) {
      console.error('Failed to complete diary:', error);
      alert('일기 저장에 실패했습니다. 다시 시도해주세요.');
    } finally {
      setIsCompleting(false);
    }
  };

  const handleEmotionSelect = (emotion: string) => {
    setSelectedEmotion(emotion);
  };

  if (!session) {
    return (
      <div className="h-full flex items-center justify-center">
        <div className="text-center">
          <EumiCharacter size="lg" mood="neutral" />
          <p className="mt-4 text-[#8B7355]">세션을 시작하고 있어요...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="h-full flex flex-col bg-gradient-to-b from-[#FFF5E6] to-[#FAF8F5]">
      {/* 헤더 */}
      <header className="bg-white/80 backdrop-blur-sm border-b border-[#E8DCC8] p-4 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <EumiCharacter size="sm" mood="happy" />
          <div>
            <h1 className="font-black text-[#6B5744] tracking-tight font-diary italic">
              이음이와 대화
            </h1>
            <p className="text-xs text-[#A0937D] font-sans-system">
              {new Date().toLocaleDateString('ko-KR', { month: 'long', day: 'numeric' })}
            </p>
          </div>
        </div>
        
        <button
          onClick={() => setIsTTSEnabled(!isTTSEnabled)}
          className="p-2.5 rounded-full hover:bg-[#F5E6D3] transition-all"
        >
          {isTTSEnabled ? (
            <Volume2 className="w-5 h-5 text-[#8B7355]" />
          ) : (
            <VolumeX className="w-5 h-5 text-[#A0937D]" />
          )}
        </button>
      </header>

      {/* 메시지 리스트 */}
      <div className="flex-1 overflow-y-auto smooth-scrollbar p-4 space-y-4">
        {session.messages.map((msg, index) => (
          <div
            key={index}
            className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'} animate-slide-up`}
          >
            {msg.role === 'assistant' && (
              <div className="mr-2 flex-shrink-0">
                <EumiCharacter size="sm" mood="happy" />
              </div>
            )}
            <div
              className={`max-w-[75%] p-4 rounded-[1.8rem] font-diary ${
                msg.role === 'user'
                  ? 'bg-gradient-primary text-white rounded-br-md shadow-md'
                  : 'bg-white text-[#6B5744] rounded-bl-md shadow-sm border border-[#E8DCC8]'
              }`}
            >
              <p className="text-sm whitespace-pre-wrap leading-relaxed">{msg.content}</p>
            </div>
          </div>
        ))}
        
        {/* 감정 선택 UI */}
        {showEmotionSelect && (
          <div className="bg-white rounded-[2.5rem] p-6 shadow-lg border-2 border-[#E8DCC8] animate-slide-up">
            <div className="flex items-center gap-2 mb-4">
              <EumiCharacter size="sm" mood="excited" />
              <p className="text-sm text-[#6B5744] font-semibold font-diary">
                오늘의 감정을 선택해주세요!
              </p>
            </div>
            
            <div className="grid grid-cols-3 gap-2.5 mb-5">
              {EMOTIONS.map((emotion) => (
                <button
                  key={emotion.name}
                  onClick={() => handleEmotionSelect(emotion.name)}
                  className={`p-4 rounded-2xl text-center transition-all ${
                    selectedEmotion === emotion.name
                      ? 'bg-gradient-primary text-white scale-105 shadow-lg'
                      : 'bg-[#FFF5E6] text-[#6B5744] hover:bg-[#F5E6D3]'
                  }`}
                >
                  <div className="text-3xl mb-1.5">{emotion.emoji}</div>
                  <div className="text-xs font-medium">{emotion.name}</div>
                </button>
              ))}
            </div>

            <div className="space-y-4">
              <div>
                <label className="text-sm text-[#8B7355] mb-2 block font-semibold">
                  만족도: {satisfaction}점
                </label>
                <input
                  type="range"
                  min="0"
                  max="100"
                  value={satisfaction}
                  onChange={(e) => setSatisfaction(Number(e.target.value))}
                  className="w-full h-2.5 bg-[#E8DCC8] rounded-full appearance-none cursor-pointer accent-[#D4AF7A]"
                  style={{
                    background: `linear-gradient(to right, #D4AF7A 0%, #D4AF7A ${satisfaction}%, #E8DCC8 ${satisfaction}%, #E8DCC8 100%)`
                  }}
                />
              </div>

              <button
                onClick={handleComplete}
                disabled={!selectedEmotion || isCompleting}
                className={`w-full py-4 rounded-[1.5rem] font-bold transition-all flex items-center justify-center gap-2 ${
                  selectedEmotion && !isCompleting
                    ? 'bg-gradient-primary text-white hover:shadow-lg active:scale-[0.98]'
                    : 'bg-[#E8DCC8] text-[#A0937D] cursor-not-allowed'
                }`}
              >
                <Check className="w-5 h-5" />
                {isCompleting ? '저장 중...' : '일기 완성하기'}
              </button>
            </div>
          </div>
        )}
        
        <div ref={messagesEndRef} />
      </div>

      {/* 입력 영역 */}
      <div className="p-4 bg-white/80 backdrop-blur-sm border-t border-[#E8DCC8]">
        <div className="flex items-center gap-2">
          <button
            onClick={isRecording ? stopRecording : startRecording}
            className={`p-3.5 rounded-full transition-all ${
              isRecording
                ? 'bg-red-500 text-white animate-pulse shadow-lg'
                : 'bg-[#F5E6D3] text-[#8B7355] hover:bg-[#E8DCC8]'
            }`}
          >
            {isRecording ? <MicOff className="w-5 h-5" /> : <Mic className="w-5 h-5" />}
          </button>

          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyPress={(e) => e.key === 'Enter' && handleSend()}
            placeholder="메시지를 입력하세요..."
            disabled={isSending || showEmotionSelect}
            className="flex-1 px-5 py-3.5 bg-[#FFF5E6] border border-[#E8DCC8] rounded-full focus:outline-none focus:ring-2 focus:ring-[#D4AF7A] text-[#6B5744] placeholder-[#A0937D] font-diary"
          />

          <button
            onClick={handleSend}
            disabled={!input.trim() || isSending || showEmotionSelect}
            className={`p-3.5 rounded-full transition-all ${
              input.trim() && !isSending && !showEmotionSelect
                ? 'bg-gradient-primary text-white hover:shadow-lg active:scale-[0.98]'
                : 'bg-[#E8DCC8] text-[#A0937D] cursor-not-allowed'
            }`}
          >
            <Send className="w-5 h-5" />
          </button>
        </div>
      </div>
    </div>
  );
}