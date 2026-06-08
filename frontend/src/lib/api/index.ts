// Frontend → Backend API 레이어 진입점.
// 경계 정책: docs는 repo 루트 INTEGRATION-BOUNDARY.md 참조 (liv-I1).
export { API_BASE, AI_ENABLED } from './config';
export { maskPII, type MaskResult } from './masking';
export { ApiError, getToken, clearToken } from './client';
export { ensureDeviceToken } from './auth';
export { sendAiChat, type AiReply } from './chat';
