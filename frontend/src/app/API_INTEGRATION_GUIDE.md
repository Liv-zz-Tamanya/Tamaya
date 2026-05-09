# 감정 일기 웹앱 - 백엔드 API 연동 가이드

## 📋 개요

이 프로젝트는 백엔드 API OpenAPI 스펙에 맞춰 구현되었습니다.
Mock 모드와 실제 API 모드를 쉽게 전환할 수 있습니다.

---

## 🔧 API 연결 설정

### 1. BASE_URL 변경

`/config/api.ts` 파일에서 실제 백엔드 서버 주소로 변경하세요:

```typescript
export const API_CONFIG = {
  BASE_URL: "https://your-actual-backend.com", // 👈 여기를 변경
  // ...
};
```

### 2. Mock 모드 끄기

실제 API를 사용하려면 `/config/api.ts`에서 Mock 모드를 비활성화하세요:

```typescript
export const USE_MOCK_DATA = false; // true → false로 변경
```

---

## 📡 API 엔드포인트

### 채팅 세션 관련

#### 1. 세션 시작/재개
- **Endpoint**: `POST /api/v1/chat/sessions`
- **설명**: 오늘의 채팅 세션을 시작하거나 기존 세션 반환
- **Response**: `ChatSessionResponse`

```json
{
  "id": "uuid",
  "session_date": "2026-02-23",
  "messages": [
    {
      "role": "assistant",
      "content": "안녕하세요! 오늘 하루는 어떠셨나요?",
      "created_at": "2026-02-23T10:00:00Z"
    }
  ],
  "is_finalized": false,
  "user_message_count": 0,
  "should_suggest_finalize": false,
  "created_at": "2026-02-23T10:00:00Z"
}
```

#### 2. 세션 조회
- **Endpoint**: `GET /api/v1/chat/sessions/{session_id}`
- **설명**: 세션 ID로 채팅 세션과 메시지 히스토리 조회
- **Response**: `ChatSessionResponse`

#### 3. 메시지 전송
- **Endpoint**: `POST /api/v1/chat/sessions/{session_id}/messages`
- **설명**: 사용자 메시지 전송 및 AI 응답 받기
- **Request Body**:
```json
{
  "content": "오늘 회사에서 프로젝트가 잘 마무리됐어요"
}
```

- **Response**: `SendMessageResponse`
```json
{
  "user_message": {
    "role": "user",
    "content": "오늘 회사에서 프로젝트가 잘 마무리됐어요",
    "created_at": "2026-02-23T10:01:00Z"
  },
  "ai_message": {
    "role": "assistant",
    "content": "프로젝트가 잘 마무리되어서 기쁘시겠어요! 어떤 점이 가장 뿌듯하셨나요?",
    "created_at": "2026-02-23T10:01:02Z"
  },
  "should_suggest_finalize": false
}
```

---

### 일기 관련

#### 4. 일기 생성 (Finalize)
- **Endpoint**: `POST /api/v1/diaries/{session_id}/finalize`
- **설명**: 채팅 세션의 대화 내용을 AI가 분석하여 일기 자동 생성
- **Response**: `DiaryResponse`

```json
{
  "id": "uuid",
  "diary_date": "2026-02-23",
  "title": "2월 23일의 일기",
  "content": "오늘은 회사에서 프로젝트를 성공적으로 마무리했다...",
  "emotion": "기쁨",
  "satisfaction": 85,
  "chat_session_id": "session-uuid",
  "created_at": "2026-02-23T10:05:00Z"
}
```

#### 5. 일기 목록 조회
- **Endpoint**: `GET /api/v1/diaries?offset=0&limit=20`
- **설명**: 작성된 일기를 최신순으로 조회 (페이지네이션)
- **Query Parameters**:
  - `offset`: 건너뛸 항목 수 (default: 0)
  - `limit`: 조회할 항목 수 (default: 20, max: 100)

- **Response**: `DiaryListResponse`
```json
{
  "items": [
    {
      "id": "uuid",
      "diary_date": "2026-02-23",
      "title": "2월 23일의 일기",
      "content": "...",
      "emotion": "기쁨",
      "satisfaction": 85,
      "chat_session_id": "session-uuid",
      "created_at": "2026-02-23T10:05:00Z"
    }
  ],
  "total": 42
}
```

#### 6. 날짜별 일기 조회
- **Endpoint**: `GET /api/v1/diaries/{diary_date}`
- **설명**: 특정 날짜(YYYY-MM-DD)의 일기 조회
- **Response**: `DiaryResponse`

---

## 🗂️ 데이터 타입

### ChatSessionResponse
```typescript
{
  id: string;                    // UUID
  session_date: string;          // YYYY-MM-DD
  messages: ChatMessageResponse[];
  is_finalized: boolean;
  user_message_count: number;
  should_suggest_finalize: boolean; // 5-7회 대화 후 true
  created_at: string;            // ISO 8601
}
```

### DiaryResponse
```typescript
{
  id: string;                    // UUID
  diary_date: string;            // YYYY-MM-DD
  title: string;
  content: string;               // AI가 대화 내용 기반 요약
  emotion: string;               // 단일 감정 (예: "기쁨", "슬픔")
  satisfaction: number;          // 0-100
  chat_session_id: string | null;
  created_at: string;            // ISO 8601
}
```

---

## 🎨 프론트엔드 구현

### 일기 작성 플로우

1. **세션 시작**: 페이지 진입 시 `POST /api/v1/chat/sessions` 호출
2. **대화 진행**: 사용자 메시지마다 `POST /api/v1/chat/sessions/{session_id}/messages` 호출
3. **감정 선택**: `should_suggest_finalize = true`가 되면 감정/만족도 선택 UI 표시
4. **일기 완성**: `POST /api/v1/diaries/{session_id}/finalize` 호출하여 일기 생성

### 캘린더 뷰 플로우

1. **월별 일기 조회**: `GET /api/v1/diaries?offset=0&limit=100` 호출
2. **프론트에서 필터링**: 응답 받은 `items` 배열을 월별로 필터링
3. **날짜 선택**: 특정 날짜 클릭 시 해당 일기 표시

---

## ⚠️ 주의사항

### 1. 감정 데이터 형식 변경

**백엔드 API는 단일 감정만 지원합니다.**

- ❌ 이전: `emotions: ["기쁨", "설렘", "행복"]` (배열)
- ✅ 현재: `emotion: "기쁨"` (단일 문자열)

프론트엔드에서 사용자가 여러 감정을 선택하더라도, 백엔드로는 대표 감정 1개만 전송됩니다.

### 2. 일기 삭제 기능 미지원

**백엔드 API에 DELETE 엔드포인트가 없습니다.**

현재는 Mock 모드에서만 삭제 기능이 작동합니다. 실제 API 연결 시:
- 삭제 버튼 숨기기 OR
- 백엔드에 DELETE 엔드포인트 추가 요청

### 3. STT/TTS API

**음성 인식/합성은 네이버 API를 사용합니다.**

백엔드에서 프록시 처리가 필요할 수 있습니다:
- `POST /api/voice/stt` - Speech to Text
- `POST /api/voice/tts` - Text to Speech

---

## 🧪 테스트

### Mock 모드에서 테스트
```typescript
// /config/api.ts
export const USE_MOCK_DATA = true; // ✅ Mock 사용
```

- 로컬 스토리지 기반 세션 관리
- 가상 AI 응답 생성
- 네트워크 없이 전체 플로우 테스트 가능

### 실제 API 모드로 전환
```typescript
// /config/api.ts
export const API_CONFIG = {
  BASE_URL: "https://your-backend.com",
  // ...
};
export const USE_MOCK_DATA = false; // ✅ 실제 API 사용
```

---

## 📦 폴더 구조

```
/config
  api.ts              ← API 설정 (BASE_URL, 엔드포인트)
  
/utils
  api.ts              ← API 호출 함수, 타입 정의
  mockData.ts         ← Mock 데이터
  rewardSystem.ts     ← 게이미피케이션 시스템
  
/components
  ChatDiary.tsx       ← 채팅 세션 기반 일기 작성
  CalendarView.tsx    ← 월별 일기 목록
  DiaryDetail.tsx     ← 일기 상세 모달
  Home.tsx            ← 홈 대시보드
  Statistics.tsx      ← 감정 통계
  Insights.tsx        ← AI 인사이트
  InventoryPage.tsx   ← 보상 인벤토리
  EumiCharacter.tsx   ← 이음이 캐릭터
  BottomNav.tsx       ← 하단 네비게이션
```

---

## 🎯 다음 단계

1. ✅ 백엔드 서버 URL 설정
2. ✅ Mock 모드 끄기
3. ⚙️ 네이버 STT/TTS API 연동 확인
4. 🧪 실제 API로 전체 플로우 테스트
5. 🐛 에러 핸들링 강화
6. 🚀 배포

---

## 💡 개발 팁

### API 에러 디버깅
```typescript
// 브라우저 콘솔에서 확인
console.log('API Error:', error);
```

### 로컬 스토리지 초기화
```javascript
// 브라우저 콘솔에서 실행
localStorage.clear();
location.reload();
```

### Mock 데이터 수정
`/utils/mockData.ts` 파일에서 테스트용 데이터를 자유롭게 수정할 수 있습니다.

---

Made with 💖 by 이음이
