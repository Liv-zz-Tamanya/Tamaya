// API 호출 유틸리티 함수
import { API_CONFIG, USE_MOCK_DATA } from '../config/api';
import { mockDiaryList, mockDailyInsight, mockWeeklyReport, mockEmotionStats } from './mockData';

// ===== 백엔드 API 타입 정의 (OpenAPI 스펙 기반) =====

export interface ChatMessageResponse {
  role: string;
  content: string;
  created_at: string;
}

export interface ChatSessionResponse {
  id: string;
  session_date: string;
  messages: ChatMessageResponse[];
  is_finalized: boolean;
  user_message_count: number;
  should_suggest_finalize: boolean;
  created_at: string;
}

export interface DiaryResponse {
  id: string;
  diary_date: string;
  title: string;
  content: string;
  emotion: string; // 단일 감정 (배열 아님)
  satisfaction: number;
  chat_session_id: string | null;
  created_at: string;
}

export interface DiaryListResponse {
  items: DiaryResponse[];
  total: number;
}

export interface SendMessageRequest {
  content: string; // max 2000자
}

export interface SendMessageResponse {
  user_message: ChatMessageResponse;
  ai_message: ChatMessageResponse;
  should_suggest_finalize: boolean;
  diary?: DiaryResponse;
}

// ===== 프론트엔드 내부 타입 (기존 호환) =====

export interface DiaryEntry {
  id: string;
  date: string;
  title?: string;
  content: string;
  emotion: string; // 단일 감정으로 변경
  satisfaction: number;
  chatLog?: ChatMessage[];
  createdAt: string;
}

export interface ChatMessage {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  timestamp: string;
}

export interface EmotionStats {
  period: 'week' | 'month';
  emotions: { name: string; count: number; emoji: string }[];
  satisfactionAvg: number;
  totalDays: number;
}

export interface DailyInsight {
  date: string;
  insight: string;
  tip: string;
}

export interface WeeklyReport {
  startDate: string;
  endDate: string;
  summary: string;
  topEmotions: string[];
  avgSatisfaction: number;
  tips: string[];
}

// 동시접속 1세션 강제 로그아웃 핸들러 (DEC-023)
// 401 수신 시 다른 기기 로그인으로 판단 → 세션 클리어 + 로그인 redirect
function handleSessionConflict(): void {
  import('sonner').then(({ toast }) => {
    toast.error(
      '다른 기기에서 로그인되어 이 기기에서 로그아웃됩니다',
      { duration: 4000 }
    );
  });
  // 세션 데이터 초기화
  localStorage.removeItem('current_session');
  localStorage.removeItem('hasVisited');
  // 로그인 화면으로 redirect (300ms 후 — 토스트 표시 후)
  setTimeout(() => {
    window.location.reload();
  }, 300);
}

// API 호출 헬퍼 함수
async function apiCall<T>(endpoint: string, options?: RequestInit): Promise<T> {
  const url = `${API_CONFIG.BASE_URL}${endpoint}`;

  const response = await fetch(url, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      ...options?.headers,
    },
  });

  // DEC-023: 동시접속 1세션 — 401 = 다른 기기 로그인으로 간주
  if (response.status === 401) {
    handleSessionConflict();
    throw new Error('SESSION_CONFLICT_401');
  }

  if (!response.ok) {
    throw new Error(`API Error: ${response.status}`);
  }

  return response.json();
}

// ===== 채팅 세션 API =====
export const chatApi = {
  // 세션 시작/재개
  async startSession(): Promise<ChatSessionResponse> {
    if (USE_MOCK_DATA) {
      const mockSession: ChatSessionResponse = {
        id: `session-${Date.now()}`,
        session_date: new Date().toISOString().split('T')[0],
        messages: [
          {
            role: 'assistant',
            content: '안녕하세요! 오늘 하루는 어떠셨나요? 편하게 이야기 나눠봐요 😊',
            created_at: new Date().toISOString(),
          }
        ],
        is_finalized: false,
        user_message_count: 0,
        should_suggest_finalize: false,
        created_at: new Date().toISOString(),
      };
      
      // 로컬 스토리지에서 오늘 세션 확인
      const savedSession = localStorage.getItem('current_session');
      if (savedSession) {
        const session = JSON.parse(savedSession);
        if (session.session_date === mockSession.session_date) {
          return Promise.resolve(session);
        }
      }
      
      localStorage.setItem('current_session', JSON.stringify(mockSession));
      return Promise.resolve(mockSession);
    }
    
    return apiCall(API_CONFIG.ENDPOINTS.CHAT_SESSION_START, {
      method: 'POST',
    });
  },

  // 세션 조회
  async getSession(sessionId: string): Promise<ChatSessionResponse> {
    if (USE_MOCK_DATA) {
      const savedSession = localStorage.getItem('current_session');
      if (savedSession) {
        return Promise.resolve(JSON.parse(savedSession));
      }
      throw new Error('Session not found');
    }
    
    return apiCall(
      API_CONFIG.ENDPOINTS.CHAT_SESSION_GET.replace(':session_id', sessionId)
    );
  },

  // 메시지 전송
  async sendMessage(sessionId: string, content: string): Promise<SendMessageResponse> {
    if (USE_MOCK_DATA) {
      const savedSession = localStorage.getItem('current_session');
      if (!savedSession) throw new Error('No active session');
      
      const session: ChatSessionResponse = JSON.parse(savedSession);
      
      // 사용자 메시지 추가
      const userMessage: ChatMessageResponse = {
        role: 'user',
        content,
        created_at: new Date().toISOString(),
      };
      
      // AI 응답 생성
      const aiResponses = [
        '그렇군요! 더 자세히 이야기해주시겠어요?',
        '정말 좋았겠네요. 그 순간 어떤 감정이었나요?',
        '잘 들었어요. 오늘 하루를 돌아보면 어떤 기분이 드시나요?',
        '네, 이해했어요. 다른 특별한 일도 있으셨나요?',
        '충분히 이야기를 나눴네요! 이제 오늘의 감정을 선택해주시겠어요?',
      ];
      
      const aiMessage: ChatMessageResponse = {
        role: 'assistant',
        content: aiResponses[Math.min(session.user_message_count, aiResponses.length - 1)],
        created_at: new Date().toISOString(),
      };
      
      // 세션 업데이트
      session.messages.push(userMessage, aiMessage);
      session.user_message_count += 1;
      session.should_suggest_finalize = session.user_message_count >= 5;
      
      localStorage.setItem('current_session', JSON.stringify(session));
      
      return Promise.resolve({
        user_message: userMessage,
        ai_message: aiMessage,
        should_suggest_finalize: session.should_suggest_finalize,
      });
    }
    
    return apiCall(
      API_CONFIG.ENDPOINTS.CHAT_MESSAGE_SEND.replace(':session_id', sessionId),
      {
        method: 'POST',
        body: JSON.stringify({ content }),
      }
    );
  },
};

// ===== 일기 API =====
export const diaryApi = {
  // 일기 완성 (채팅 세션 기반)
  async finalize(sessionId: string): Promise<DiaryResponse> {
    if (USE_MOCK_DATA) {
      const savedSession = localStorage.getItem('current_session');
      if (!savedSession) throw new Error('No active session');
      
      const session: ChatSessionResponse = JSON.parse(savedSession);
      
      // 대화 내용 요약
      const userMessages = session.messages
        .filter(m => m.role === 'user')
        .map(m => m.content)
        .join(' ');
      
      const newDiary: DiaryResponse = {
        id: `diary-${Date.now()}`,
        diary_date: session.session_date,
        title: `${new Date(session.session_date).toLocaleDateString('ko-KR', { month: 'long', day: 'numeric' })}의 일기`,
        content: userMessages || '오늘 하루를 보냈습니다.',
        emotion: '행복', // 기본값
        satisfaction: 70, // 기본값
        chat_session_id: session.id,
        created_at: new Date().toISOString(),
      };
      
      // Mock 데이터에 추가
      const existingIndex = mockDiaryList.findIndex(d => d.date === newDiary.diary_date);
      if (existingIndex > -1) {
        mockDiaryList[existingIndex] = {
          ...mockDiaryList[existingIndex],
          id: newDiary.id,
          content: newDiary.content,
          emotion: newDiary.emotion,
          satisfaction: newDiary.satisfaction,
          createdAt: newDiary.created_at,
        };
      } else {
        mockDiaryList.push({
          id: newDiary.id,
          date: newDiary.diary_date,
          title: newDiary.title,
          content: newDiary.content,
          emotion: newDiary.emotion,
          satisfaction: newDiary.satisfaction,
          createdAt: newDiary.created_at,
        });
      }
      
      // 세션 초기화
      localStorage.removeItem('current_session');
      
      return Promise.resolve(newDiary);
    }
    
    return apiCall(
      API_CONFIG.ENDPOINTS.DIARY_FINALIZE.replace(':session_id', sessionId)
    );
  },

  // 일기 목록 조회 (페이지네이션)
  async getList(year?: number, month?: number, offset = 0, limit = 100): Promise<DiaryListResponse> {
    if (USE_MOCK_DATA) {
      let filtered = [...mockDiaryList];
      
      if (year && month) {
        filtered = filtered.filter(diary => {
          const date = new Date(diary.date);
          return date.getFullYear() === year && date.getMonth() + 1 === month;
        });
      }
      
      const items = filtered.slice(offset, offset + limit);
      
      return Promise.resolve({
        items,
        total: filtered.length,
      });
    }
    
    const params = new URLSearchParams({
      offset: offset.toString(),
      limit: limit.toString(),
    });
    
    return apiCall(`${API_CONFIG.ENDPOINTS.DIARY_LIST}?${params}`);
  },

  // 날짜별 일기 조회
  async getByDate(date: string): Promise<DiaryResponse> {
    if (USE_MOCK_DATA) {
      const diary = mockDiaryList.find(d => d.date === date);
      if (!diary) throw new Error('Diary not found');
      
      return Promise.resolve({
        id: diary.id,
        diary_date: diary.date,
        title: diary.title || `${new Date(date).toLocaleDateString('ko-KR')}의 일기`,
        content: diary.content,
        emotion: diary.emotion,
        satisfaction: diary.satisfaction,
        chat_session_id: null,
        created_at: diary.createdAt,
      });
    }
    
    return apiCall(
      API_CONFIG.ENDPOINTS.DIARY_BY_DATE.replace(':diary_date', date)
    );
  },

  // 일기 삭제 (백엔드 API에 없음 - Mock만 지원)
  async delete(id: string): Promise<void> {
    if (USE_MOCK_DATA) {
      const index = mockDiaryList.findIndex(d => d.id === id);
      if (index > -1) {
        mockDiaryList.splice(index, 1);
      }
      return Promise.resolve();
    }
    
    // 백엔드 API에 삭제 엔드포인트가 없으므로 에러
    throw new Error('Delete operation not supported by backend API');
  },
};

// ===== 감정 API (Mock only - 백엔드에 없음) =====
export const emotionApi = {
  // 감정 통계 조회
  async getStats(period: 'week' | 'month'): Promise<EmotionStats> {
    if (USE_MOCK_DATA) {
      return Promise.resolve(mockEmotionStats);
    }
    
    // 백엔드 API 없음 - 프론트에서 계산
    const diaries = await diaryApi.getList();
    
    // 통계 계산 로직
    const emotionCount: Record<string, number> = {};
    let totalSatisfaction = 0;
    
    diaries.items.forEach(diary => {
      emotionCount[diary.emotion] = (emotionCount[diary.emotion] || 0) + 1;
      totalSatisfaction += diary.satisfaction;
    });
    
    const emotions = Object.entries(emotionCount).map(([name, count]) => ({
      name,
      count,
      emoji: '😊', // 기본 이모지
    }));
    
    return {
      period,
      emotions,
      satisfactionAvg: diaries.items.length > 0 ? totalSatisfaction / diaries.items.length : 0,
      totalDays: diaries.items.length,
    };
  },
};

// ===== 인사이트 API (Mock only - 백엔드에 없음) =====
export const insightApi = {
  // 일일 인사이트
  async getDaily(date: string): Promise<DailyInsight> {
    if (USE_MOCK_DATA) {
      return Promise.resolve(mockDailyInsight);
    }
    
    // 백엔드 API 없음
    return Promise.resolve({
      date,
      insight: 'AI가 분석한 인사이트가 여기 표시됩니다.',
      tip: '꾸준히 일기를 작성해보세요!',
    });
  },

  // 주간 리포트
  async getWeekly(): Promise<WeeklyReport> {
    if (USE_MOCK_DATA) {
      return Promise.resolve(mockWeeklyReport);
    }
    
    // 백엔드 API 없음
    return Promise.resolve({
      startDate: new Date().toISOString().split('T')[0],
      endDate: new Date().toISOString().split('T')[0],
      summary: '이번 주 리포트입니다.',
      topEmotions: ['행복'],
      avgSatisfaction: 70,
      tips: ['꾸준히 기록해보세요!'],
    });
  },
};

// 음성 API (네이버)
export const voiceApi = {
  // STT (Speech to Text)
  async speechToText(audioBlob: Blob): Promise<string> {
    if (USE_MOCK_DATA) {
      // Mock STT response
      return Promise.resolve('오늘 하루는 정말 좋았어요');
    }
    
    const formData = new FormData();
    formData.append('audio', audioBlob);
    
    const response = await fetch(`${API_CONFIG.BASE_URL}${API_CONFIG.ENDPOINTS.NAVER_STT}`, {
      method: 'POST',
      body: formData,
    });

    if (!response.ok) {
      throw new Error('STT failed');
    }

    const data = await response.json();
    return data.text;
  },

  // TTS (Text to Speech)
  async textToSpeech(text: string): Promise<Blob> {
    if (USE_MOCK_DATA) {
      // Mock TTS - 빈 오디오 Blob 반환
      return Promise.resolve(new Blob([], { type: 'audio/mp3' }));
    }
    
    const response = await fetch(`${API_CONFIG.BASE_URL}${API_CONFIG.ENDPOINTS.NAVER_TTS}`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ text }),
    });

    if (!response.ok) {
      throw new Error('TTS failed');
    }

    return response.blob();
  },
};

// 타입 export
export type Diary = DiaryEntry;