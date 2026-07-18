// Frontend → Backend API 레이어 진입점.
// 경계 정책: docs는 repo 루트 INTEGRATION-BOUNDARY.md 참조 (liv-I1).
export { API_BASE, AI_ENABLED } from './config';
export { maskPII, type MaskResult } from './masking';
export { ApiError, getToken, clearToken } from './client';
export {
  ensureDeviceToken,
  getDeviceId,
  checkNickname,
  signupWithNickname,
  loginWithNickname,
  getNickname,
} from './auth';
export {
  clearChatSessionCache,
  sendAiChat,
  startAiChatSession,
  type AiReply,
  type ChatSessionMaxTurns,
  type GeneratedDiaryResponse,
} from './chat';
export { listDiaries, type DiaryResponse, type DiaryListResponse } from './diaries';

// 건강냥(Medlife) 통합 — BE-only 기능 클라이언트 (feat/healthcat-backend)
export { sendCoachingMessage, type CoachTurn } from './coaching';
export {
  getWeeklyInsight,
  getMonthlyInsight,
  isoWeekOf,
  monthOf,
  type InsightResponse,
  type WellbeingReport,
  type TrendPoint,
} from './insight';
export {
  getClovaSetting,
  testClovaKey,
  saveClovaKey,
  type ClovaSetting,
  type ClovaTestResult,
} from './clova';
export { sendHealthChat } from './healthchat';
export { purgeMyData, type PurgeResult } from './me';
export {
  getNightChatPreference,
  updateNightChatPreference,
  type NightChatPreference,
} from './preferences';
