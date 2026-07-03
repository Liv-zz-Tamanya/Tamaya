# NCP 자원 생성 가이드

단일 VM에 docker-compose로 백엔드+DB를 띄우고, 프론트는 Object Storage + CDN+로 정적 호스팅하는 구성.

> NCP 콘솔 UI는 자주 바뀝니다. 메뉴명은 비슷한 위치에서 찾으면 됩니다.

---

## 0. 사전 준비

- **NCP 계정**: <https://www.ncloud.com> 가입 + 결제수단 등록 (체크카드/신용카드)
- **도메인**: 가비아/카페24/Cloudflare 중 하나에서 보유 (예: `tamanya.com`)
  - 서브도메인 계획
    - `tamanya.com` → 프론트 (CDN+)
    - `api.tamanya.com` → 백엔드 (VM)
- **SSH 키페어**: 로컬에서 미리 생성

  ```bash
  ssh-keygen -t ed25519 -C "tamanya-ncp" -f ~/.ssh/tamanya_ncp
  # → ~/.ssh/tamanya_ncp (private), ~/.ssh/tamanya_ncp.pub (public)
  ```

- **플랫폼 선택**: 콘솔 우측 상단에서 `VPC` 선택 (Classic 아님)
- **리전**: `KR (한국)` 권장

---

## 1. VPC + Subnet

콘솔 메뉴: `Services > Networking > VPC`

### 1-1. VPC 생성

| 항목 | 값 |
|---|---|
| VPC 이름 | `tamanya-vpc` |
| IP 주소 범위 | `10.0.0.0/16` |

### 1-2. Subnet 생성

`Subnet Management > Subnet 생성`

| 항목 | 값 |
|---|---|
| Subnet 이름 | `tamanya-public-subnet` |
| VPC | `tamanya-vpc` |
| IP 주소 범위 | `10.0.1.0/24` |
| Internet Gateway 전용 여부 | **Public** |
| 용도 | `일반` (General) |

> Public Subnet이어야 외부에서 접근 가능.

---

## 2. Server (VM) 생성

콘솔 메뉴: `Services > Compute > Server`

### 2-1. 서버 이미지 선택

- 종류: **Ubuntu Server 22.04 (LTS)**
- 아키텍처: `x86`

### 2-2. 서버 스펙

| 항목 | 값 | 비고 |
|---|---|---|
| 서버 타입 | `High CPU` 또는 `Standard` | `s2-g3` (2vCPU/4GB) 이상 |
| 스토리지 종류 | `SSD` | |
| 스토리지 크기 | `50GB` | sentence-transformers 모델, Docker 이미지 고려 |

> **메모리 권장**: 4GB는 최소. `paraphrase-multilingual-MiniLM-L12-v2` 모델(약 470MB) + Postgres + FastAPI 동시 구동이면 **8GB(`s2-g3`/`m2-g3`)** 가 안전.

### 2-3. 서버 세부 설정

| 항목 | 값 |
|---|---|
| 서버 이름 | `tamanya-api-01` |
| VPC | `tamanya-vpc` |
| Subnet | `tamanya-public-subnet` |
| 네트워크 인터페이스 | 자동 할당 |
| 반납 보호 | (선택) ON 권장 |
| 요금제 | `월요금제` 또는 `시간요금제` |

### 2-4. 인증키

- **새로운 인증키 생성** 또는 위에서 만든 SSH 공개키 등록
- 자동 생성 선택 시 `.pem` 파일을 안전한 곳에 보관

### 2-5. ACG (Access Control Group)

서버 생성 마지막 단계에서 ACG 선택/생성. **이 단계에서 ACG 생성하지 말고**, 일단 기본 ACG로 진행한 뒤 3번에서 따로 설정.

### 2-6. 관리자 비밀번호 확인

생성 후 `서버 관리 및 설정 변경 > 관리자 비밀번호 확인` 메뉴에서 `.pem` 키로 비밀번호 복호화. (root 비밀번호로 첫 SSH 접속에 사용 가능)

---

## 3. ACG (방화벽) 설정

콘솔 메뉴: `Server > ACG`

### 3-1. ACG 생성

- 이름: `tamanya-api-acg`
- VPC: `tamanya-vpc`

### 3-2. 인바운드 규칙

| 프로토콜 | 접근 소스 | 허용 포트 | 메모 |
|---|---|---|---|
| TCP | `내 IP/32` | `22` | SSH (본인 IP만) |
| TCP | `0.0.0.0/0` | `80` | HTTP (Let's Encrypt 인증, HTTPS 리다이렉트) |
| TCP | `0.0.0.0/0` | `443` | HTTPS |

> **5432 (Postgres)는 절대 외부에 열지 말 것.** docker-compose 내부 네트워크로만 접근.

### 3-3. 서버에 ACG 적용

`Server 목록 > 서버 선택 > ACG 수정 > tamanya-api-acg` 추가, `default` 제거 (또는 default도 함께 유지).

---

## 4. Public IP

콘솔 메뉴: `Server > Public IP`

- `공인 IP 신청`
- 서버 선택: `tamanya-api-01`
- 신청 완료 후 IP 메모 (예: `223.130.x.x`)

> Public IP는 서버에 연결되어 있을 때는 무료, 미연결 시 과금됨.

---

## 5. Object Storage (프론트 정적 호스팅)

콘솔 메뉴: `Services > Storage > Object Storage`

### 5-1. 버킷 생성

| 항목 | 값 |
|---|---|
| 버킷 이름 | `tamanya-web` (전 세계 유일해야 함) |
| 권한 설정 | **공개 (Public Read)** |

### 5-2. 정적 웹 호스팅 활성화

`버킷 상세 > 정적 웹사이트 호스팅 설정`

| 항목 | 값 |
|---|---|
| 사용 여부 | `사용함` |
| Index Document | `index.html` |
| Error Document | `index.html` *(SPA fallback)* |

> Vite SPA는 클라이언트 라우팅이므로 모든 404를 `index.html`로 보내야 함.

### 5-3. 엔드포인트 확인

- `https://kr.object.ncloudstorage.com/tamanya-web/index.html` 같은 URL이 발급됨
- 이걸 CDN+ Origin으로 사용

### 5-4. CORS 설정 (필요시)

API 도메인과 다르면 CORS가 필요. 다만 우리는 프론트 도메인 = `tamanya.com`, API = `api.tamanya.com`로 같은 부모 도메인이라 백엔드 FastAPI 측 CORS만 잘 설정하면 OK.

---

## 6. CDN+ 설정

콘솔 메뉴: `Services > Content Delivery > CDN+`

### 6-1. CDN+ 프로필 생성

| 항목 | 값 |
|---|---|
| 프로필 이름 | `tamanya-web-cdn` |
| 서비스 프로토콜 | `HTTPS` |
| 서비스 도메인 | (자동 발급 후 CNAME으로 연결) |

### 6-2. Origin 설정

| 항목 | 값 |
|---|---|
| Origin 종류 | **Object Storage** |
| 버킷 | `tamanya-web` |

### 6-3. 인증서

`Services > Security > Certificate Manager`에서 무료 인증서 발급:

1. 인증서 신청 → 도메인 입력 (`tamanya.com`)
2. DNS 검증 또는 이메일 검증
3. 발급 완료 후 CDN+ 프로필에 인증서 연결

### 6-4. 사용자 도메인 연결

CDN+ 프로필 상세 > `사용자 도메인 추가`에서 `tamanya.com` 입력. 발급된 CNAME 값을 DNS에 등록 (7번 참조).

---

## 7. DNS 설정

도메인 등록 기관(가비아/카페24/Cloudflare 등) DNS 관리에서:

| 타입 | 호스트 | 값 | TTL |
|---|---|---|---|
| **A** | `api` | `<2-6에서 받은 Public IP>` | 300 |
| **CNAME** | `@` 또는 `www` | `<CDN+에서 받은 엔드포인트>` | 300 |

> `@`(루트 도메인)에 CNAME이 안 되는 DNS 제공자라면 ALIAS/ANAME 사용. 안 되면 NCP의 `Global DNS`로 옮기는 것도 옵션.

DNS 전파는 보통 5분~수 시간.

---

## 8. (선택) Container Registry

GitHub Actions에서 Docker 이미지를 빌드해 NCP에 push하려면 필요. **단순 SSH + git pull 방식이면 생략 가능.**

콘솔 메뉴: `Services > Container > Container Registry`

- 레지스트리 생성: `tamanya-registry`
- 엔드포인트: `<region>.ncr.ntruss.com`
- 접근키 (API Authentication Key)는 `My Page > 계정관리 > 인증키 관리`에서 발급

---

## 9. 비용 가이드 (대략, 2025년 KR 리전 기준)

| 자원 | 월 예상 | 메모 |
|---|---|---|
| Server `s2-g3` (2vCPU/8GB) | 4~5만원 | 시간요금제 24/7 |
| 스토리지 50GB SSD | 약 5천원 | 서버에 포함 |
| Public IP | 약 4천원 | 미연결 시만 과금 |
| Object Storage | 1~3천원 | 트래픽/용량 미미 |
| CDN+ | 트래픽에 비례 | MVP 수준이면 월 수천원 |
| Certificate Manager | 무료 | |
| **합계** | **6~8만원/월** | |

> 첫 결제 시 NCP 신규 가입 크레딧이 있으면 일부 차감됨. 정확한 견적은 [NCP 요금 계산기](https://www.ncloud.com/charge/calc) 참조.

---

## 10. 체크리스트

- [ ] VPC + Public Subnet 생성
- [ ] Server (Ubuntu 22.04, 8GB RAM) 생성 + SSH 키 등록
- [ ] ACG 인바운드 22/80/443만 허용 (5432 차단)
- [ ] Public IP 발급 + 서버 연결 + IP 메모
- [ ] Object Storage 버킷 생성 + 정적 호스팅 활성화 + Index/Error: `index.html`
- [ ] Certificate Manager에서 도메인 인증서 발급
- [ ] CDN+ 프로필 생성 + Object Storage origin 연결 + 인증서 연결
- [ ] DNS A 레코드 (`api.도메인` → Public IP)
- [ ] DNS CNAME (`@`/`www` → CDN+ 엔드포인트)
- [ ] `ssh ubuntu@<Public IP>` 접속 확인

위 체크리스트 다 완료되면 **VM 초기 셋업** 단계로 진행:

- Docker, docker-compose, nginx, certbot 설치
- Git clone, `.env.production` 작성
- Let's Encrypt 인증서 발급 (`certbot --nginx -d api.tamanya.com`)
- `nginx-api.conf` 적용 + `nginx -t && systemctl reload nginx`
- `docker compose -f docker-compose.prod.yml up -d --build`
