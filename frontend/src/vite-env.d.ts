/// <reference types="vite/client" />

interface ImportMetaEnv {
  /** Backend API base URL (FastAPI). 기본 http://localhost:8000 */
  readonly VITE_API_BASE?: string;
  /** AI 채팅 backend 결선 on/off. 'false'면 로컬 시뮬레이션만 사용 */
  readonly VITE_AI_ENABLED?: string;
  /** 데모/개발 편의: 고정 device_id로 시드 데이터 확인. production 미설정 */
  readonly VITE_DEMO_DEVICE_ID?: string;
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}
