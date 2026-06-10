# Tamaya — Frontend ↔ Backend 데이터 경계 (liv-I1 Private-First)

*2026-06-08 · liv-zz CTO · 연동 레이어 신설(0단계 선행 설계) · 관련: liv-I1 Private-First / liv-I4 마스킹 ≥95% / PDL-050 SEC On-Demand*

## 원칙 (절대)

> **일기 원문(diary body)은 기기를 떠나지 않는다.** 서버로 가는 것은 (1) AI 대화에 필요한 **마스킹된 텍스트**, (2) auth 토큰, (3) (향후) **암호화된 요약/메타**뿐이다. 원문 평문은 어떤 경로로도 서버에 전송·저장하지 않는다.

## 경계표

| 데이터 항목 | 온디바이스(localStorage) | 서버 전송 | 마스킹/암호화 | 근거 |
|---|---|---|---|---|
| **일기 원문 `DiaryEntry.body`** | ✅ 정본 보관 | ❌ **전송 안 함** | — | liv-I1 (원문 평문 서버 금지) |
| 일기 메타(감정·키워드·체크·날짜) | ✅ | ⚠️ 향후 sync 시 **암호화 요약만** | 암호화 | 통계/백업용, 원문 제외 |
| **AI 채팅 사용자 발화** (home-day `aiChat`) | ✅ 표시용 원문 | ✅ **마스킹 후** 전송 | **PII 마스킹**(`api/masking.ts`) | AI/CLOVA 경유 불가피 → PII 제거 후 |
| AI 응답(CLOVA mock/실) | ✅ 표시 | ✅ 서버 생성 | — | 응답은 서버 생성물 |
| 채팅 세션 id | ✅ 캐시 | ✅ (세션 키만) | — | 대화 컨텍스트 유지 |
| **저녁 회고 5턴 `chatDiary` → 일기 작성** | ✅ **로컬 전용** | ❌ | — | 일기 작성 플로우 = 원문 영역, 서버 미접촉 |
| auth / device_id | ✅ 토큰·device_id 캐시 | ✅ `POST /auth/device` | 토큰(JWT) | 익명 device 인증 |
| daily 체크·캐릭터·포인트·게임 | ✅ | ⏳ 향후(서버 게임 테이블 존재) | — | 현 PoC는 로컬, 서버 결선은 후속 |

## 흐름 요약

```
[home-day AI 채팅]  user 발화(원문) ──localStorage(표시)
                          │
                    maskPII()  ← PII 제거 (전화/이메일/주민/카드/장기숫자)
                          │ (마스킹된 텍스트만)
                          ▼
        POST /api/v1/chat/sessions/{id}/messages  → ai_message(CLOVA mock)
                          │
                          ▼
                    bot 응답 표시 + localStorage

[저녁 회고 → 일기 저장]  chatDiary 5턴 → DiaryEntry.body 생성
                          └─ localStorage 전용 (diary/save). 서버 호출 0.  ← liv-I1
```

## 마스킹 책임 분계 (PDL-050)

- **현재(프론트 1차 방어선)**: `frontend/src/lib/api/masking.ts` — 경량 정규식(전화·이메일·주민·카드·장기숫자). AI 경로 전송 직전 적용.
- **본 구현(SEC On-Demand)**: 문맥 기반 이름·주소·민감표현 마스킹 = patent-pending 파이프라인. HCX 실연동 트리거 시 SEC 재호출(PDL-050). 프론트 마스킹은 그 전까지의 최소 가드이며 ≥95%(liv-I4) 보증은 SEC 본구현이 책임.

## 환경

- `VITE_API_BASE` (기본 `http://localhost:8000`) — backend FastAPI. `frontend/.env.example` 참조.
- backend `CLOVA_MOCK_MODE=true` (실 NCP 키 수령 전, DEC-022.4) — AI 응답은 mock으로 발현.

---

## 🚩 미해결 경계 — `feat/healthcat-backend` 통합 (2026-06-11, liv-zz CTO)

건강냥이 BE 통합으로 **서버 전송 표면이 넓어졌다**. 다음은 production 진입 전 반드시 결정해야 할 경계 항목(현재 PoC 배선은 "전송 가능"을 증명한 것이지 "전송해야 함"을 결정한 게 아님):

| 데이터/기능 | 현재(PoC 브랜치) | 미해결 결정 | 정합 Invariant |
|---|---|---|---|
| **밤 코칭 발화** (S23 → `/api/v1/coaching/messages`) | maskPII 후 전송, history 클라 보관, BE 세션 미보관 | 코칭 정성신호(emotion/behavior)가 서버에 영속됨 — 원문 대비 무엇을 저장/폐기할지 보존정책 | liv-I1 / liv-I4(≥95%) |
| **건강 기록 RAG** (S26 → `/api/v1/health-chat`) | 세션·메시지 서버 보관, 건강기록 embedding 검색 | 건강기록(생체·복약 등) 자체의 서버 보관 = liv-I1 "생체 raw 온디바이스" 원칙과 정면 충돌 가능 → **온디바이스 RAG vs 서버 RAG** 결정 | **liv-I1 (생체 raw)** |
| **데일리체크·일기·통계** (S08·S11/12·S16) | 로컬 store 전용(미배선) | 서버 배선 시 일기 원문/체크가 서버로 — 현 SSOT는 "일기 원문 서버 0". 배선 범위·마스킹·암호화 확정 필요 | liv-I1 |
| **BYOK CLOVA 키** (S25 → `/settings/clova`) | 마스킹(••••last4)만 저장, 원문 미저장 | 키 회전·만료·디바이스 변경 시 정책 | (보안 일반) |
| **마스킹 본 구현** | FE maskPII 경량 정규식(1차 방어선) | HCX 실연동 트리거 시 SEC On-Demand 재호출(PDL-050) — 문맥기반 ≥95% | liv-I4 |

> **결론**: 통합 브랜치는 "FE 22화면 + 건강냥이 BE가 한 저장소에서 빌드·기동되고, 신규 4기능이 실 BE에 배선됨"을 달성. **단 일기 원문·건강 raw의 서버 전송 여부는 미결** — 위 표 결정 전 production 배포 금지. 마스킹 본 구현은 SEC On-Demand 사안.
