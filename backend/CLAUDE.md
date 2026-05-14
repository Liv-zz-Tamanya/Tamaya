# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

대화형 인터페이스를 통해 하루의 감정과 경험을 기록하고, 감정 흐름을 인식하도록 돕는 **감정 일기 서비스**의 백엔드 MVP.

### 핵심 기능

- **AI 대화 일기 작성**: 타이핑/음성 입력으로 AI와 대화하며 하루를 정리 (하루 1개 기준 저장)
- **감정 기록**: 사용자가 감정을 직접 선택하고 하루 만족도를 입력
- **캘린더 시각화**: 월별 캘린더에 날짜별 감정 이모지 표시
- **인사이트 제공**: 일일 인사이트 및 주간 리포트로 감정 패턴 요약 + 텍스트 기반 행동 팁 제공

### MVP 범위

- 감정 분석 모델 없이 **사용자 선택 기반 감정 기록**에 집중
- AI 채팅, 요약 일기 작성 등은 **네이버 클로바 API** 활용
- AI 스피커 및 음성 인터페이스 확장을 고려한 구조

## Tech Stack

- **Language**: Python 3.13+
- **Package Manager**: uv
- **Framework**: FastAPI
- **DB**: PostgreSQL + SQLAlchemy (Docker compose로 실행)
- **Infra**: Docker Compose (DB, Redis, Vector DB 등)
- **AI**: 네이버 클로바 API (채팅, 요약, 일기 생성)

## Commands

```bash
# FastAPI 서버 실행
uv run uvicorn app.main:app --reload

# 의존성 관리
uv add <package>
uv sync

# 인프라 (DB, Redis 등)
docker-compose up -d
docker-compose down
```

## Architecture

**클린 아키텍처 + DDD(유연하게 적용)** 지향. 의존성은 항상 안쪽(도메인)을 향한다.

```
app/
├── main.py              # FastAPI 앱 진입점
├── domain/              # 도메인 레이어
│   ├── model/           # 엔티티, 값 객체, 도메인 모델
│   └── repository/      # 리포지토리 인터페이스 (추상)
├── application/         # 애플리케이션 레이어
│   ├── usecase/         # 유스케이스 (비즈니스 로직 오케스트레이션)
│   └── service/         # 도메인 서비스 (복잡한 도메인 로직)
├── infrastructure/      # 인프라 레이어
│   ├── persistence/     # SQLAlchemy 리포지토리 구현체, DB 모델
│   ├── external/        # 외부 API 클라이언트 (클로바 등)
│   └── config/          # 설정, DB 연결 등
└── presentation/        # 프레젠테이션 레이어
    └── router/          # FastAPI 라우터, 스키마(DTO)
```

### 레이어 규칙

- **domain**: 외부 의존성 없음. 순수 Python 객체. SQLAlchemy 등 프레임워크 임포트 금지
- **application**: 도메인 모델과 리포지토리 인터페이스만 의존
- **infrastructure**: 구체적 구현 (DB, 외부 API). 도메인 인터페이스를 구현
- **presentation**: FastAPI 라우터. usecase를 호출하여 요청 처리

### 의존성 방향

```
presentation → application → domain ← infrastructure
```

infrastructure는 domain의 인터페이스를 구현하되, domain은 infrastructure를 모른다.

## Code Style

- **Pythonic하고 클린한 코드** 작성
- 타입 힌트 필수 사용
- 네이밍: snake_case (변수/함수), PascalCase (클래스)
- 로컬에서는 `FastAPI 실행만`, DB/Redis 등 외부 서비스는 모두 **Docker Compose**로 관리