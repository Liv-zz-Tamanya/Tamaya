# Tamanya 배포 (NCP · https://tamaya.online)

VM 1대에 `docker compose`로 **DB + 백엔드 + 프론트(nginx) + Caddy(HTTPS)** 를 전부 띄우는 구성.
접속: **<https://tamaya.online>** (www·공인 IP HTTP 접속은 여기로 리다이렉트).

- 도메인 `tamaya.online` (가비아) — A 레코드 `@`·`www` → 공인 IP
- HTTPS는 맨 앞의 **Caddy**가 종단 — Let's Encrypt 발급·갱신 자동, 인증서는 `caddy_data` 볼륨에 보존
- 프론트·백엔드가 **같은 출처** → CORS 설정 불필요
- 외부에 열리는 포트: **22(SSH), 80(HTTP→HTTPS 리다이렉트), 443(HTTPS)**. DB(5432)는 내부 전용.

---

## A. NCP 콘솔에서 자원 만들기 (당신이 함)

처음이면 [backend/deploy/ncp-setup.md](backend/deploy/ncp-setup.md)의 1~4번(VPC · Server · ACG · Public IP)만 하면 됩니다. **Object Storage/CDN(5,6번)은 이번엔 안 씀.** 요약:

1. **가입/결제수단 등록** — <https://www.ncloud.com>, 우측 상단 플랫폼 `VPC` 선택, 리전 `KR`.
2. **VPC + Public Subnet** 생성 (가이드 1번).
3. **Server 생성** (가이드 2번):
   - 이미지: **Ubuntu Server 22.04 (LTS)**, x86
   - 스펙: **메모리 8GB 권장** (`s2-g3`/`m2-g3` 급). 백엔드가 AI 모델(torch/sentence-transformers)을 쓰므로 4GB는 빌드 중 메모리 부족 위험. 8GB가 안전.
   - 스토리지: SSD **50GB**
   - 인증키(SSH `.pem`) 다운로드 후 안전 보관
4. **ACG(방화벽)** 인바운드 규칙:
   | 프로토콜 | 접근 소스 | 포트 | 메모 |
   |---|---|---|---|
   | TCP | `내 IP/32` | 22 | SSH |
   | TCP | `0.0.0.0/0` | 80 | HTTP (HTTPS로 리다이렉트 + ACME 챌린지) |
   | TCP | `0.0.0.0/0` | 443 | HTTPS |
   > 5432(DB)는 열지 마세요. UDP 443은 선택(HTTP/3).
5. **Public IP 신청 + 서버에 연결** → IP 메모 (예: `223.130.x.x`).
6. **SSH 접속 확인**:
   ```bash
   chmod 400 ~/Downloads/키파일.pem
   ssh -i ~/Downloads/키파일.pem root@<공인IP>
   ```
   (Ubuntu 이미지는 `root` 로 접속. NCP는 최초 `관리자 비밀번호 확인` 메뉴에서 `.pem`으로 비밀번호를 복호화해야 할 수도 있음 — 가이드 2-6.)

---

## B. VM 초기 셋업 (SSH 접속 후, 한 번만)

```bash
# 1) 시스템 업데이트 + Docker 설치
apt-get update && apt-get -y upgrade
curl -fsSL https://get.docker.com | sh          # Docker + compose plugin 설치
docker version && docker compose version         # 확인

# 2) (8GB 미만 VM이면 권장) 스왑 4GB — 빌드 중 OOM 방지
fallocate -l 4G /swapfile && chmod 600 /swapfile
mkswap /swapfile && swapon /swapfile
echo '/swapfile none swap sw 0 0' >> /etc/fstab

# 3) 코드 받기 (아래 URL은 이 저장소 주소로 교체)
apt-get install -y git
git clone <이_저장소_URL> tamanya
cd tamanya
git checkout feat/nickname-auth   # 배포할 브랜치
```

---

## C. 시크릿 파일 작성 (`.env.production`, VM에서)

저장소 루트에 `.env.production` 을 새로 만듭니다 (git에 올라가지 않음):

```bash
cd ~/tamanya
cat > .env.production <<'EOF'
# --- DB ---
POSTGRES_USER=aidiary
POSTGRES_PASSWORD=<강력한_비밀번호로_교체>
POSTGRES_DB=aidiary
DATABASE_URL=postgresql+asyncpg://aidiary:<위와_같은_비밀번호>@db:5432/aidiary

# --- CLOVA (네이버 HyperCLOVA X) ---
CLOVA_API_KEY=<발급받은_CLOVA_키>
CLOVA_BASE_URL=https://clovastudio.stream.ntruss.com/v1/openai
CLOVA_MODEL=HCX-005
CLOVA_MOCK_MODE=false

# --- 카카오(선택, 안 쓰면 비워둠) ---
KAKAO_APP_KEY=

# --- JWT 서명 시크릿 (반드시 랜덤값) ---
JWT_SECRET=<아래_명령으로_생성한_값>
EOF
```

`JWT_SECRET`, `POSTGRES_PASSWORD` 랜덤값 생성:
```bash
openssl rand -hex 32   # 두 번 실행해서 각각 붙여넣기
```

> 로컬 `backend/.env` 에 이미 쓰던 실제 CLOVA 키가 있으면 그 값을 `CLOVA_API_KEY` 에 넣으면 됩니다. `DATABASE_URL` 의 호스트는 반드시 `db` (compose 서비스명).

---

## D. 실행

```bash
cd ~/tamanya
docker compose --env-file .env.production -f docker-compose.prod.yml up -d --build
```

- 최초 빌드는 백엔드가 torch 등 큰 패키지를 받아 **10~20분** 걸릴 수 있음.
- 상태 확인 / 로그:
  ```bash
  docker compose -f docker-compose.prod.yml ps
  docker compose -f docker-compose.prod.yml logs -f backend   # 마이그레이션·기동 로그
  ```

브라우저에서 **<https://tamaya.online>** 접속 → 앱이 뜨면 성공.
API 문서는 `https://tamaya.online/docs`.

> 첫 기동 시 Caddy가 Let's Encrypt 인증서를 발급받습니다(수 초~1분). DNS의 A 레코드
> (`@`·`www` → 공인 IP)가 전파된 뒤여야 하며, 실패 시 Caddy가 자동 재시도합니다.
> 로그 확인: `docker compose -f docker-compose.prod.yml logs -f caddy`

---

## E. 자주 쓰는 운영 명령

```bash
# 코드 업데이트 후 재배포
git pull && docker compose --env-file .env.production -f docker-compose.prod.yml up -d --build

# 중지 / 재시작
docker compose -f docker-compose.prod.yml down
docker compose --env-file .env.production -f docker-compose.prod.yml up -d

# DB 백업 (컨테이너 → 파일)
docker compose -f docker-compose.prod.yml exec db pg_dump -U aidiary aidiary > backup_$(date +%F).sql
```

---

## F. GitHub Actions 자동 배포 (CI/CD)

**방식**: GitHub Actions가 코드를 VM으로 `rsync` 밀어넣고 → VM에서 `docker compose up --build`.
VM은 GitHub에서 코드를 당겨오지 않으므로 **VM에 GitHub 자격증명(deploy key/PAT)이 필요 없음**. 워크플로: [.github/workflows/deploy.yml](.github/workflows/deploy.yml).

> 전제: VM에 Docker 설치 + `~/tamanya/.env.production` 작성 + CI 공개키가 `~/.ssh/authorized_keys` 에 등록되어 있어야 함.

### F-1. GitHub Actions → VM 접속용 키

- CI 키쌍을 하나 만들어 **공개키는 VM `~/.ssh/authorized_keys`** 에, **개인키는 GitHub Secret `NCP_SSH_KEY`** 에 넣는다.
- 이 저장소는 조직 정책상 **Deploy key 비활성화**라 VM-쪽 git pull 대신 rsync push 방식을 씀.

### F-2. GitHub Secrets 3개

저장소 → **Settings → Secrets and variables → Actions**:

| Secret | 값 |
|---|---|
| `NCP_HOST` | VM 공인 IP (`101.79.22.108`) |
| `NCP_USER` | `root` |
| `NCP_SSH_KEY` | CI 개인키 전체 |

### F-3. 배포

`main` / `feat/nickname-auth` 에 push하면 자동 실행. 수동은 Actions 탭 → **Deploy to NCP → Run workflow**, 또는:

```bash
gh workflow run "Deploy to NCP" --ref feat/nickname-auth
```

→ **Actions 탭**에서 진행 확인. 완료되면 <https://tamaya.online> 반영. `.env.production` 은 rsync `--exclude` 로 보존됨.

---

## 다음 단계 (실사용으로 갈 때)

1. ~~도메인 구매~~ → `tamaya.online` (가비아, 2026-07-23)
2. ~~HTTPS~~ → Caddy + Let's Encrypt 적용 (2026-07-23, [Caddyfile](Caddyfile))
3. 필요 시 프론트를 Object Storage+CDN으로 분리 (원래 [ncp-setup.md](backend/deploy/ncp-setup.md) 구성) — 트래픽 커질 때.
