# PersonalAssistantAgent 오프라인 평가 데이터셋 (초안)

이 디렉터리는 실제 LLM API를 호출하지 않는 첫 번째 평가 데이터셋 초안이다. 실행기나
점수 계산기는 아직 포함하지 않으며, 현재 Agent의 mode, 도구 범위, 가드레일 계약을
검토 가능한 JSONL로 고정한다. **모든 행은 가상 사례이며, 평가 실행에 사용하기 전에
반드시 사람이 검수해야 한다.**

## 현재 코드 기준 계약

`PersonalAssistantMode`의 실제 직렬화 값은 다음과 같다.

| mode | 등록 도구 |
| --- | --- |
| `diary` | `search_diary_memories`, `search_health_records` |
| `health` | `search_health_records` |
| `coaching` | 없음 |

의료 가드레일은 `health`와 `coaching` mode에서 최신 사용자 입력만 보고 처리한다.
`safe`는 통과하고, `advice_boundary` 또는 `emergency`는 LLM/도구 호출 전에 고정
면책 응답으로 차단한다. `diary` mode에는 현재 의료 가드레일이 적용되지 않는다.

실제 실행 결과에서 도구 호출은 `AgentExecutionRecord.tool_names`로 확인할 수 있다.
이는 Agent trace가 AI message의 `tool_calls`에서 수집한 이름이다.

## 파일과 데이터 수

- `datasets/diary_cases.jsonl`: 10개
- `datasets/health_cases.jsonl`: 10개
- `datasets/coaching_cases.jsonl`: 10개
- `datasets/guardrail_cases.jsonl`: 20개

각 JSONL 행은 `PersonalAssistantEvalCase`이며 다음 필드를 가진다.

```text
id, mode, input, history, expected_tools, forbidden_tools,
expected_guardrail, expected_document_ids, category, note
```

`mode`에는 현재 enum의 실제 값(`diary`, `health`, `coaching`)을 사용한다.
`expected_document_ids`는 이 초안에서 가상의 fixture 식별자다. 실제 실행기를 만들 때
동일한 ID를 갖는 비식별 fixture corpus를 별도로 제공해야 한다.

## 작성과 검수

1. 실제 사용자 정보, 실제 건강 기록, 직접 식별 가능한 내용을 넣지 않는다.
2. 코드에 등록된 도구 이름과 해당 mode의 도구 범위만 사용한다.
3. 응답 문장 자체를 정답으로 정하지 않고 도구/가드레일/문서 기대값만 기록한다.
4. `medical_keyword_false_positive` 또는 note가 있는 행은 현재 결정론 가드레일의
   오탐·정책 경계를 보여 주므로 제품·안전 담당자가 반드시 검수한다.
5. 검색 결과가 없는 경우는 `expected_document_ids: []`로 기록하되, 도구 호출 여부는
   요청 의도에 맞게 별도로 명시한다.

## 검증

백엔드 디렉터리에서 실행한다.

```bash
uv run python -m evals.validate_dataset
uv run pytest tests/evals/test_validate_dataset.py
```

validator는 JSONL 파싱, 전역 ID 중복, mode/스키마, 빈 input, expected/forbidden 도구
중복, 현재 등록되지 않은 도구 이름, mode에서 사용할 수 없는 expected 도구를 검사한다.
현재 등록 도구 이름은 도구 생성 함수에서 직접 읽어 검사하므로 문서만 보고 추측하지 않는다.
