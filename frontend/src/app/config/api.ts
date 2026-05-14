// API 설정 파일
// BASE_URL은 .env / .env.production 의 VITE_API_BASE_URL 로 설정

export const API_CONFIG = {
  BASE_URL: import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000",
  ENDPOINTS: {
    // 채팅 세션 관련
    CHAT_SESSION_START: "/api/v1/chat/sessions", // POST - 세션 시작/재개
    CHAT_SESSION_GET: "/api/v1/chat/sessions/:session_id", // GET - 세션 조회
    CHAT_MESSAGE_SEND: "/api/v1/chat/sessions/:session_id/messages", // POST - 메시지 전송

    // 일기 관련
    DIARY_FINALIZE: "/api/v1/diaries/:session_id/finalize", // POST - 일기 생성
    DIARY_LIST: "/api/v1/diaries", // GET - 일기 목록 조회
    DIARY_BY_DATE: "/api/v1/diaries/:diary_date", // GET - 날짜별 일기 조회

    // 음성 (네이버 API) - 백엔드에서 프록시 처리
    NAVER_STT: "/api/voice/stt",
    NAVER_TTS: "/api/voice/tts",
  },
};

// Mock 모드 설정 (개발 중에는 true, 백엔드 연결 시 false)
export const USE_MOCK_DATA = true;