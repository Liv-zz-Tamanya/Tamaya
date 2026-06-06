# Figma → Frontend 워크플로우 (Tamaya Web)

> **목표**: Figma 디자인의 이미지·구체 디자인 포인트를 살려, 풀 반응형(reflow) React 페이지로 구현.
> **핵심 원칙**: **파일 비종속(file-agnostic)**. 특정 Figma 파일에 락 걸지 않는다 — 어떤 디자이너 파일이 와도 같은 파이프라인에 꽂힌다.

---

## 0. 왜 이 구조인가 — "다양한 방향성 호환"

디자인 파일은 바뀐다(디자이너 협업·리브랜딩·트랙 B 톤 스위치). 코드가 특정 파일 ID에 묶이면 그때마다 재작업이다. 그래서 Figma 와 코드 사이에 **중간 호환 레이어(interop layer)**를 둔다. 파일은 이 레이어 위로 교체되는 "입력"일 뿐이다.

```
┌──────────────────────────────────────────────────────────────┐
│  Figma 파일  (디자이너 작업 — 교체 가능한 입력, URL 파라미터)      │
│  · Variables (색·간격·타입)   · Components (버튼·카드·탭바…)      │
└───────────────────────┬──────────────────────────────────────┘
                        │  Figma MCP (get_variable_defs / get_code / get_image)
                        ▼
┌──────────────────────────────────────────────────────────────┐
│  INTEROP LAYER  ★ 파일 비종속 — 호환성의 중심축                  │
│  ① Design Tokens   : Figma Variables → src/styles/tokens.css   │
│  ② Code Connect    : Figma Component ↔ React Component 매핑      │
│                      (*.figma.tsx — 안정적 컴포넌트 identity)    │
└───────────────────────┬──────────────────────────────────────┘
                        ▼
┌──────────────────────────────────────────────────────────────┐
│  Responsive Frontend  (React + 풀 reflow)                      │
│  src/styles/responsive.css · breakpoint · reflow primitives     │
│  mobile(탭바) → tablet(중앙) → desktop(사이드네비+2컬럼)         │
└──────────────────────────────────────────────────────────────┘
```

새 Figma 파일이 와도 바꾸는 건 **①토큰 재생성 + ②매핑 갱신**뿐. 컴포넌트·반응형 로직은 그대로다.

---

## 1. 1회성 연결 (Figma MCP 인증)

Figma 를 코드에서 직접 읽으려면 MCP OAuth 가 필요하다(세션당 1회).
- CTO 세션에서 `mcp__plugin_figma_figma__authenticate` → 받은 URL 브라우저 승인 → 콜백 URL 회신.
- 인증되면 `get_code` · `get_image` · `get_variable_defs` 등 read 도구 활성화.

---

## 2. 디자인 토큰 재생성 (파일이 바뀔 때마다)

**SSOT = `src/styles/tokens.css`.** 컴포넌트 CSS 는 raw hex/px 금지, `var(--token)`만 참조.

1. 정본 Figma 파일에서 Variables 추출:
   - MCP `get_variable_defs` (대상 프레임/파일 지정)
2. 출력(색)을 `tokens.css` 의 `COLOR` 블록에 반영 — **변수 이름 1:1 유지** (`--paper`, `--accent` …).
3. SPACE/RADIUS/TYPE/BREAKPOINT 스케일은 코드 SSOT — 디자인과 합의해 갱신.
4. `pnpm build` 로 회귀 확인.

> 토큰 이름이 일치하는 한, 색만 바뀐 새 파일은 토큰 교체만으로 전 화면에 전파된다.

---

## 3. Code Connect 매핑 (컴포넌트 단위, 1회 + 변경 시)

목적: Figma 노드로 코드를 뽑을 때, 새로 생성하지 말고 **실제 React 컴포넌트를 재사용**하게.

- 설정: `figma.config.json` (parser: react, include: `src/**/*.figma.tsx`).
- 컴포넌트마다 `<Component>.figma.tsx` 작성. 패턴:

```tsx
// src/components/Button.figma.tsx  (예시 — 실제 node URL 은 OAuth 후 채움)
import figma from '@figma/code-connect';
import { Button } from './primitives';

figma.connect(Button, 'https://figma.com/design/<FILE>?node-id=<NODE>', {
  props: {
    label: figma.string('Label'),
    variant: figma.enum('Variant', { Primary: 'primary', Ink: 'ink', Ghost: 'ghost' }),
  },
  example: ({ label, variant }) => <Button variant={variant}>{label}</Button>,
});
```

- 게시: `pnpm exec figma connect publish` → Figma Dev Mode 에 코드 스니펫 노출.
- 파일이 바뀌면 node URL 만 갱신(컴포넌트 매핑 구조는 유지).

---

## 4. 화면 구현 — 풀 반응형 reflow

전략(확정): 단순 스케일 ❌ → **폭에 따라 구조 재구성**.

| 브레이크포인트 | 폭 | 레이아웃 |
|---|---|---|
| mobile | ~479px | 단일 컬럼 · 하단 탭바 · full-bleed |
| tablet | 480~1023 | 넓은 단일 컬럼 · 중앙 정렬(`--app-max`) |
| desktop | 1024px~ | 사이드 네비(`--sidenav-w`) + 콘텐츠 2컬럼 |

- 프리미티브: `responsive.css` 의 `.app-layout` · `.app-sidenav` · `.reflow-grid` · `.reflow-stack` · `.container--app` · `.show-desktop`/`.hide-desktop`.
- 유동 타이포: 고정 px 대신 `clamp()` (`.fluid-display` 등).
- 이미지/구체 포인트 살리기:
  - 벡터/아이콘 → MCP `get_code` 로 SVG 직접 추출 → 인라인 컴포넌트.
  - 사진/래스터 → MCP `get_image` → `public/assets/` 저장 → `srcset` 반응형.
- 화면당 절차: Figma 노드 → `get_code`/`get_image` → 토큰·프리미티브로 재조립 → 3 브레이크포인트 확인.

---

## 5. 빠른 명령 모음

```bash
pnpm --dir frontend dev            # 개발 서버 (localhost:5173)
pnpm --dir frontend build          # tsc + vite 빌드 (회귀 게이트)
pnpm --dir frontend exec figma connect publish   # Code Connect 게시 (OAuth 후)
```

---

## 6. 현재 상태 (2026-06-01 세팅)

- [x] Figma MCP 서버 설치 (`plugin:figma:figma`) — **OAuth 대기**
- [x] `tokens.css` interop SSOT (Coffee Palette + 스케일)
- [x] `responsive.css` reflow 파운데이션 (3 브레이크포인트 + 프리미티브)
- [x] `@figma/code-connect@1.4.7` + `figma.config.json`
- [ ] 정본 Figma 파일 URL 확보 (디자이너 협업본) → 토큰 재생성 + Code Connect node URL 채우기
- [ ] S01~S22 화면 풀 reflow 적용 (구현 단계 — FE)
