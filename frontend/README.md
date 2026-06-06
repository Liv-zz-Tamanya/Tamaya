# Tamaya (이음:me) — Frontend Prototype

밤에 깨어나는 고양이 집사와 매일 작은 루틴을 키우는 **Private-First 대화형 라이프케어 일기** 프로토타입.
Vite + React 18 + TypeScript. **백엔드 불필요** — 모든 데이터는 브라우저 `localStorage`(온디바이스, liv-I1 Private-First)에만 저장됩니다.

## 빠른 시작

```bash
# 1) 의존성 설치 (pnpm 권장 — pnpm-lock.yaml 포함. npm/yarn도 가능)
pnpm install

# 2) 개발 서버 (http://localhost:5173)
pnpm dev

# 3) 프로덕션 빌드 / 미리보기
pnpm build      # tsc -b + vite build → dist/
pnpm preview
```

요구 사항: **Node 18+** (개발 검증 Node 22). 그 외 환경변수·`.env`·API 키·외부 서버 **불필요**.

## 두 가지 모드

| URL | 모드 | 설명 |
|---|---|---|
| `http://localhost:5173/` | **앱 미리보기** | 22화면 인터랙티브 폰 셸. 상단 툴바로 화면 점프 + 시간대(낮/밤) 토글 |
| `http://localhost:5173/#design` | **와이어프레임 캔버스** | 전체 화면을 아트보드로 한눈에 + 팔레트/vibe/density 토글 |

## 구조

```
src/
├── main.tsx · App.tsx        # 진입 + 앱/캔버스 모드 스위치
├── lib/
│   ├── router.ts             # 22 Route + NavContext(시간대 night 포함)
│   └── store.tsx             # localStorage 전역 store(reducer) + 시드 일기 + 통계 집계
├── components/               # AppShell · DesignCanvas · TweaksPanel · primitives
├── screens/                  # onboarding · home-day · evening · records · character · login · settings
└── styles/                   # tokens(디자인 토큰 SSOT) · responsive · sketch
```

## 데이터 초기화

브라우저 콘솔 또는 설정(S22) "데이터 초기화" 버튼:

```js
localStorage.removeItem('tamaya-state-v2'); location.reload();
```

> 참고: 일기 원문·감정 데이터는 서버로 전송되지 않습니다(온디바이스 우선). AI 응답·통계는 현재 로컬 시뮬레이션이며, 실제 LLM(HCX) 연동은 백엔드 단계입니다.
