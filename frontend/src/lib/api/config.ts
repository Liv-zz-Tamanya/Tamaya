// API 환경 설정.
// API base는 VITE_API_BASE로 주입(없으면 로컬 backend). 뒤 슬래시는 제거.
export const API_BASE: string = (
  import.meta.env.VITE_API_BASE || 'http://localhost:8000'
).replace(/\/+$/, '');

// AI 채팅을 backend(CLOVA, MOCK 가능)로 결선할지 여부.
// 'false'로 두면 프론트 로컬 시뮬레이션(simulateAiReply)만 사용.
export const AI_ENABLED: boolean = import.meta.env.VITE_AI_ENABLED !== 'false';
