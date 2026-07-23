// A11Y-12: prefers-reduced-motion 존중 — 시스템이 모션 축소를 요청하면 스크롤을
// 즉시 이동(auto)으로, 아니면 기존처럼 부드럽게(smooth) 수행한다.
// 로직 불변 — scrollTo 호출부의 대상·타이밍은 그대로, behavior 값만 이 헬퍼로 통일.
export const scrollBehavior = (): ScrollBehavior =>
  matchMedia('(prefers-reduced-motion: reduce)').matches ? 'auto' : 'smooth';
