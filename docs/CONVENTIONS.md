## 1. 언어

**커밋 제목·본문·브랜치명 모두 영어.**

-   브랜치명은 처음부터 100% 영어였고, 커밋 제목도 2026-07-18부터 영어로 전환됨. 그 방향으로 확정.
-   소문자로 시작. 고유명사(CLOVA, Alembic, Agent 등)는 원표기 유지.
-   PR 본문과 코드 주석은 한국어 허용. 히스토리에 남는 것만 영어.

---

## 2. 브랜치

```
<type>/<kebab-case-summary>
```

**type** (커밋 타입과 동일한 어휘 사용)

| type       | 용도                     |
| ---------- | ------------------------ |
| `feat`     | 기능 추가                |
| `fix`      | 버그 수정                |
| `refactor` | 동작 변경 없는 구조 개선 |
| `test`     | 테스트 추가·정비         |
| `chore`    | 설정, 의존성, 빌드       |
| `docs`     | 문서만 변경              |
| `ci`       | 워크플로 변경            |

**규칙**

-   summary는 2~4단어, 명사구. 도메인 → 대상 순서.
    -   `feat/personal-assistant-timeout`, `fix/health-data-isolation` (기존 패턴 그대로)
-   이슈 번호는 브랜치명에 넣지 않는다. PR 본문에 `Closes #12`로 연결.
-   한 브랜치 = 한 PR = 한 관심사. 브랜치가 3일 이상 살아있으면 쪼갤 신호.
-   머지 후 원격 브랜치 삭제.

**베이스 브랜치**

-   모든 작업 브랜치는 `main`에서 딴다.
-   `develop`은 사용하지 않는다. (현재 main보다 124커밋 뒤처진 상태 — 정리 대상)
-   보존 목적의 스냅샷은 브랜치가 아니라 **태그**로 남긴다.
    -   `legacy/phone-preview` → `git tag archive/phone-preview <sha>` 후 브랜치 삭제
    -   `mvp-version-1` → `git tag v0.1.0-mvp` 후 브랜치 삭제

---

## 3. 커밋 메시지

```
<type>(<scope>): <subject>

<body — 왜 이렇게 했는가>

Refs: #<issue>
```

### 3.1 type

브랜치 type 표와 동일. 추가로 아래 둘만 허용:

| type    | 용도                                      |
| ------- | ----------------------------------------- |
| `style` | 포맷·디자인 토큰 등 동작에 영향 없는 변경 |
| `perf`  | 성능 개선                                 |

**`polish`는 사용하지 않는다.** 기존 `polish` 커밋들은 내용상 아래로 분류된다.

-   빈 상태 UI 추가 → `feat`
-   하드코딩 → 실데이터 바인딩 → `fix` 또는 `refactor`
-   디자인 토큰 정합 → `style`

### 3.2 scope

**아래 3개만 사용. 없으면 생략한다.**

| scope      | 범위                                                |
| ---------- | --------------------------------------------------- |
| `backend`  | `backend/**`                                        |
| `frontend` | `frontend/**`                                       |
| `infra`    | docker-compose, Makefile, `.github/workflows`, 배포 |

-   양쪽에 걸치면 scope를 생략한다.
-   **우선순위(P0/P1/P2)는 scope가 아니다.** 이슈·PR 라벨로 관리한다.
-   도메인(agent, auth, diary, health, clova 등)은 scope가 아니라 subject 안에 쓴다.
    -   ❌ `feat(chat): ...` ✅ `feat(backend): add turn limit to recap chat session`

### 3.3 subject

-   명령형 현재시제. `add`, `fix`, `remove`, `move` — `added`/`adding` 아님
-   소문자 시작, 마침표 없음
-   50자 이내
-   "무엇을 했는지"를 쓴다. "왜"는 body로.

### 3.4 body

**선택이지만, 아래 경우엔 필수:**

-   원인이 자명하지 않은 버그 수정
-   성능·구조상 트레이드오프가 있는 선택
-   외부 제약(CLOVA API 스펙, Alembic head, iOS safe-area 등) 때문에 우회한 구현

형식은 자유. 다만 **"왜"와 "무엇을 안 골랐는지"** 두 가지를 남긴다.

```
perf(backend): use CPU-only torch on linux

GPU 빌드는 이미지가 8.7GB까지 커져 배포 파이프라인이 타임아웃.
추론은 CLOVA 원격 호출이라 로컬 GPU가 불필요해 CPU 휠로 교체.
→ 1.5GB. 추후 온디바이스 추론이 필요해지면 이 결정을 되돌려야 함.
```

이 body가 저녁 devlog와 ADR의 원재료가 된다. 여기서 안 남기면 하루 뒤엔 복구 불가.

### 3.5 한 커밋 = 한 관심사

기능 추가와 리팩터링을 한 커밋에 섞지 않는다.
같은 PR 안에서 `refactor:` → `feat:` → `test:` 순으로 쪼갠다. (기존에 잘 하고 계신 패턴)

---

## 4. PR · 머지

-   **머지 커밋 방식 유지** (squash 하지 않음).
    `git log --merges`로 PR 단위 작업 이력을 그대로 뽑을 수 있어야 하기 때문. devlog 자동 생성이 이 히스토리에 의존한다.
-   PR 제목은 커밋 제목과 동일한 형식을 따른다: `feat(backend): ...`
-   PR 본문 최소 3줄: **무엇을 / 왜 / 어떻게 검증했는지**
-   이슈 연결: `Closes #12`

---

## 5. 자동 검사 (선택)

컨벤션은 사람이 지키면 깨진다. 강제하려면:

**commitlint** — 커밋 시점에 차단

```bash
npm i -D @commitlint/{cli,config-conventional} husky
echo "module.exports = {extends:['@commitlint/config-conventional']}" > commitlint.config.js
npx husky init && echo "npx commitlint --edit \$1" > .husky/commit-msg
```

**Claude Code hook** — Claude가 만드는 커밋에도 적용
`.claude/settings.json`의 `PreToolUse` 훅에서 `git commit` 명령을 검사해 형식이 어긋나면 차단.
CLAUDE.md에 적어두는 것은 요청이고, 훅은 강제다. 반드시 지켜야 하는 규칙이면 훅으로 옮긴다.
