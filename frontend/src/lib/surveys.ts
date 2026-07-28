// PM 제작 예정 설문 링크 모음 — 완성되면 URL만 채우면 된다.
// 빈 문자열이면 소비처에서 "준비 중" 안내로 폴백한다.

/** 이음이 키우기(방·옷장) 기능 의견 설문 */
export const CAT_SURVEY_URL = '';

/** 건강 기록 기능(출시 예정) 의견 설문 */
export const HEALTH_SURVEY_URL = '';

/** 설문을 새 창으로 연다. URL이 아직 없으면 false를 반환한다. */
export const openSurvey = (url: string): boolean => {
  if (!url) return false;
  window.open(url, '_blank', 'noopener,noreferrer');
  return true;
};
