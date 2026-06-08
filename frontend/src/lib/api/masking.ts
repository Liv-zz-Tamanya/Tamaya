// ── 온디바이스 PII 마스킹 (PRE-SEND GUARD) ──────────────────────────────────
//
// AI 채팅 텍스트가 서버(CLOVA)로 떠나기 직전 적용하는 1차 방어선.
// 일기 원문 자체는 서버로 보내지 않는다(liv-I1). 이 함수는 'AI 경로로 보내는
// 발화'에서 식별정보(PII)를 제거한다.
//
// ⚠️ 경량 정규식 마스킹(전화·이메일·주민·카드·장기숫자)일 뿐이다.
//    문맥 기반 이름·주소·민감표현 등 본 마스킹 파이프라인(특허출원)은 SEC 영역 —
//    HCX 실연동 시 PDL-050 On-Demand로 본구현 트리거. liv-I4(≥95%) 보증은 SEC 책임.

export type MaskResult = {
  /** 마스킹 적용된 텍스트 (서버로 전송 가능) */
  text: string;
  /** 마스킹된 항목 수 */
  masked: number;
  /** 마스킹된 PII 유형 목록 */
  types: string[];
};

// 순서 중요: 더 구체적인 패턴(이메일·주민·카드·전화)을 장기숫자 폴백보다 먼저.
const RULES: { type: string; re: RegExp; rep: string }[] = [
  { type: 'email', re: /[\w.+-]+@[\w-]+\.[\w.-]+/g, rep: '[이메일]' },
  { type: 'rrn', re: /\b\d{6}[-\s]?[1-4]\d{6}\b/g, rep: '[주민번호]' },
  { type: 'card', re: /\b(?:\d{4}[-\s]?){3}\d{4}\b/g, rep: '[카드번호]' },
  { type: 'phone', re: /\b01[016789][-\s]?\d{3,4}[-\s]?\d{4}\b/g, rep: '[전화번호]' },
  // 위 패턴에 안 걸린 8자리 이상 연속 숫자(계좌 등) 폴백
  { type: 'longnum', re: /\b\d{8,}\b/g, rep: '[숫자]' },
];

/** 텍스트에서 PII를 마스킹한다. 원본은 변형하지 않고 새 문자열을 반환. */
export function maskPII(input: string): MaskResult {
  let text = input;
  let masked = 0;
  const types: string[] = [];
  for (const { type, re, rep } of RULES) {
    text = text.replace(re, () => {
      masked += 1;
      if (!types.includes(type)) types.push(type);
      return rep;
    });
  }
  return { text, masked, types };
}
