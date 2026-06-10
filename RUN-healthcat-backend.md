# RUN — Tamaya FE + 건강냥이 BE 통합 (`feat/healthcat-backend`)

> 브랜치: `feat/healthcat-backend` · 생성 2026-06-11 · liv-zz CTO
> Vite FE(이음:me 22화면) + 건강냥이 BE(8 라우터·coaching·insight·settings 포함)를 한 저장소에서 기동.
> **로컬 빌드/실행 전용 — push 보류**(대상 repo PUBLIC 미결, ED 결정 대기).

---

## 0. 구성

```
liv-zz-poc/  @ feat/healthcat-backend
├── frontend/   # Vite + React 18 + TS — 이음:me 22화면 + 신규 4화면(S23~S26)
│   └── src/lib/api/   # auth·chat·coaching·insight·clova·healthchat (BE 클라이언트)
├── backend/    # FastAPI Clean-arch + DDD — 건강냥이 BE(동기화), pgvector RAG
├── docker-compose.yml  # Postgres(pgvector pg16)
└── Makefile    # up / down / be / fe / migrate / dev
```

## 1. 사전 요건

- **Docker** (Postgres pgvector) · **Python ≥ 3.13 + [uv](https://docs.astral.sh/uv/)** · **Node ≥ 18 + pnpm**

## 2. 백엔드 (건강냥이) 기동

```bash
# 1) Postgres(pgvector) 컨테이너
make up                                   # = docker compose up -d postgres  (localhost:5432, aidiary/aidiary)

# 2) 백엔드 의존성 설치 (건강냥이 superset: langgraph·sentence-transformers·pgvector 포함)
cd backend && uv sync                     # ⚠️ 기존 .venv는 구 backend용 → 반드시 재동기화
cp .env.example .env                      # CLOVA_MOCK_MODE=true (NCP 키 없이 mock 동작)

# 3) 마이그레이션 (clova_settings·qualitative_signals 포함 전체)
cd .. && make migrate                     # = cd backend && alembic upgrade head

# 4) (선택) 웰빙 인사이트(S24)·건강 RAG(S26)용 합성 시드 — liv-I1: 실데이터 금지, 합성만
cd backend && uv run python scripts/seed_demo_signals.py

# 5) 서버 기동 (포트 8000)
cd .. && make be                          # = uvicorn app.main:app --reload --port 8000
#   확인: curl http://localhost:8000/health  → {"status":"ok"}
#         http://localhost:8000/docs        → OpenAPI (auth·chat·coaching·diary·game·health-chat·insight·settings)
```

> **CLOVA_MOCK_MODE=true** (기본): NCP HCX 키 없이 mock 응답. 실 키 수령 시 `.env`에서 `false` + `CLOVA_API_KEY` 설정(DEC-022.4). BYOK는 앱 내 S25(CLOVA 키)에서 키별 등록 가능.

## 3. 프론트엔드 (Tamaya) 기동

```bash
cd frontend
cp .env.example .env        # VITE_API_BASE=http://localhost:8000 · VITE_AI_ENABLED=true
pnpm install
pnpm dev                    # http://localhost:5173
# 프로덕션 빌드 검증: pnpm build  (tsc -b && vite build — ✅ 통과 확인됨)
```

- CORS: 건강냥이 BE가 `localhost:5173`(+3000·127.0.0.1)을 이미 허용(`backend/app/main.py`).
- **오프라인/ BE 미기동이어도 앱은 동작**: AI 채팅(S09)·로그인(S21)은 실패 시 로컬 폴백/graceful 진입.

## 4. 동작 확인 포인트 (이 브랜치에서 실제 BE 배선된 것)

| 화면 | 엔드포인트 | 확인 |
|---|---|---|
| **S09 낮 AI 코칭** | `POST /api/v1/chat/sessions/{id}/messages` | 메시지 전송 → mock CLOVA 응답 (maskPII 후 전송) |
| **S21 로그인** | `POST /auth/device` | 익명/카카오 버튼 → device 토큰 확보(JWT) 후 온보딩 |
| **S23 밤 코칭** | `POST /api/v1/coaching/messages` | 건강냥 코칭 대화(guardrail-first, history 클라보관) |
| **S24 웰빙 인사이트** | `GET /api/v1/insights/weekly` | 주간 웰빙 스코어+trend (시드 없으면 빈 상태 UI) |
| **S25 CLOVA 키(BYOK)** | `/api/v1/settings/clova` (test·PUT·GET) | 키 연결테스트·마스킹 저장 |
| **S26 건강 기록 Q&A** | `POST /api/v1/health-chat/sessions/.../messages` | 건강기록 RAG 챗 (시드 권장) |

> 신규 4화면(S23~S26)은 설정(S22) 화면 또는 상단 툴바 드롭다운에서 진입. 전체 화면 상태: [`projects/liv-zz/artifacts/tamaya-screens-wireframe.html`](../../Documents/Project/projects/liv-zz/artifacts/tamaya-screens-wireframe.html)

## 5. 아직 로컬 store 전용(배선 미완) — 다음 단계

데일리체크(S08)·5턴 일기(S11/12)·달력(S14/15)·통계(S16/17)·키우기(S18~20)는 **렌더 완성·`store.tsx`(localStorage) 로컬 전용**. 일부는 BE 엔드포인트가 없거나(home·daily-check·stats·character actions) 경로/스키마 정합이 필요(diary month·finalize). 기능별 상세: [`projects/liv-zz/artifacts/tamaya-integration-feature-comparison.html`](../../Documents/Project/projects/liv-zz/artifacts/tamaya-integration-feature-comparison.html).

## 6. ⚠️ liv-I1 Private-First 경계 (미해결 플래그)

데일리체크·일기 등을 서버로 보내는 배선은 **PoC 단계**다. FE `store.tsx`의 "localStorage만·서버 DB 미사용" 원칙과 충돌하므로, **무엇을 온디바이스 유지 / 무엇을 (마스킹·암호화 후) 서버 전송할지** production 경계 결정이 선행돼야 한다. 현 SSOT 및 미해결 항목: [`INTEGRATION-BOUNDARY.md`](./INTEGRATION-BOUNDARY.md).
