// API 설정 파일 — 명세(feature-spec v3) /v1 계약
// BASE_URL은 .env / .env.production 의 VITE_API_BASE_URL 로 설정

export const API_CONFIG = {
  BASE_URL: import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000",
  ENDPOINTS: {
    // F1 — 인증
    AUTH_ANONYMOUS: "/v1/auth/anonymous", // POST
    AUTH_REFRESH: "/v1/auth/refresh", // POST

    // F1 — 온보딩 + 캐릭터
    ONBOARDING_CONSENT: "/v1/onboarding/privacy-consent", // POST
    ONBOARDING_COMPLETE: "/v1/onboarding/complete", // POST
    CHARACTER: "/v1/character", // POST(생성) / GET(조회)

    // F4 — 데일리 체크
    DAILY_CHECK_DATE: "/v1/daily-check/:date", // PUT / GET
    DAILY_CHECK_MONTH: "/v1/daily-check", // GET ?month=YYYY-MM

    // F5 — 일기 작성
    DIARY_SESSION_START: "/v1/diary-session/start", // POST
    DIARY_SESSION_TURN: "/v1/diary-session/:session_id/turn", // POST
    DIARY_SESSION_FINALIZE: "/v1/diary-session/:session_id/finalize", // POST
    DIARY_SAVE: "/v1/diary", // POST
    DIARY_LIST: "/v1/diary", // GET ?month=YYYY-MM
    DIARY_BY_DATE: "/v1/diary/:diary_date", // GET

    // 음성 (네이버 API) - 백엔드 프록시 (P1)
    NAVER_STT: "/api/voice/stt",
    NAVER_TTS: "/api/voice/tts",
  },
};

// 실제 백엔드 연동 (목업 비활성화)
export const USE_MOCK_DATA = false;

// 토큰/디바이스 localStorage 키
export const STORAGE_KEYS = {
  ACCESS: "tamaya_access_token",
  REFRESH: "tamaya_refresh_token",
  DEVICE: "tamaya_device_id",
};
