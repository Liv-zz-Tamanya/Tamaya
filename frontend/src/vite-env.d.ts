/// <reference types="vite/client" />

interface ImportMetaEnv {
  /** Backend API base URL (FastAPI). 기본 http://localhost:8000 */
  readonly VITE_API_BASE?: string;
  /** AI 채팅 backend 결선 on/off. 'false'면 로컬 시뮬레이션만 사용 */
  readonly VITE_AI_ENABLED?: string;
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}
