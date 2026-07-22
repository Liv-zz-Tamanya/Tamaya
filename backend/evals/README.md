# PersonalAssistantAgent 오프라인 평가 데이터셋 (초안)

이 디렉터리는 PersonalAssistantAgent의 Tool routing과 Guardrail만 측정하는 오프라인
평가 도구다. 최종 답변 품질과 RAG 정확도는 평가하지 않는다. 모든 입력은 합성 사례이며
실행기는 production DB나 사용자 데이터에 접근하지 않는다.

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
`expected_document_ids`는 보고서에 보존하지만 현재 상태는 항상 `not_evaluated`다. 다음
단계에서 비식별 fixture corpus와 RAG 검색 평가를 추가한다.

## Tool decision 평가

`expected_decision`은 선택 필드이며 `NO_TOOL` 또는 `TOOL_CALL` 값을 사용한다. `NO_TOOL`은
별도 Tool이 아니라 Agent가 실제 실행된 뒤 모델 응답에 `tool_calls`가 없는 직접 응답을 뜻한다. Runner는 명시된 값이
없어도 `expected_tools`가 있으면 `TOOL_CALL`, expected tool 없이 forbidden tool만 있으면
`NO_TOOL`로 측정용 추론을 한다. 기존 Tool/Guardrail/Combined 판정은 이 지표로 바뀌지 않는다.

보고서는 Decision checks, NO_TOOL accuracy, TOOL_CALL accuracy, unnecessary tool call count를
별도로 저장한다. unnecessary tool call은 NO_TOOL 기대 실행에서 하나 이상 Tool이 호출된 경우다.
Decision 지표는 Agent가 실제로 실행되어 직접 응답 또는 Tool Call을 선택한 경우만 평가한다.
입력 Guardrail이 Agent 실행 전에 차단한 요청과 실행 오류는 NO_TOOL/TOOL_CALL 정확도에서 제외하고
`Decision skipped` 및 사유별 건수로 별도 보고한다. Guardrail 평가와 기존 Combined 판정에는 영향을 주지 않는다.

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

## 실행

실행기는 실제 CLOVA Tool Calling 모델을 호출하므로 비용이 발생할 수 있다. `CLOVA_MOCK_MODE=false`와
`CLOVA_API_KEY`가 필요하며, mock model은 실제 도구 선택을 평가할 수 없어 CLI에서 거부한다.

```bash
uv run python -m evals.run_evaluation
uv run python -m evals.run_evaluation --dataset health --limit 3
uv run python -m evals.run_evaluation --case-id diary-001
uv run python -m evals.run_evaluation --fail-on-mismatch
```

반복 실행과 안정성 비교도 지원한다.

```bash
# 선택한 각 case를 5회 실행
uv run python -m evals.run_evaluation --dataset diary --repeat 5

# 특정 case의 변동성 확인
uv run python -m evals.run_evaluation --case-id diary-004 --repeat 10

# 이전 안정성 리포트와 rate 기준 비교
uv run python -m evals.run_evaluation --dataset diary --repeat 5 \
  --baseline evals/reports/diary-baseline.json --fail-on-regression
```

`cases`는 execution 단위 결과다. 따라서 `--repeat 5`면 같은 case ID가 `run_number` 1부터
5까지로 다섯 번 저장된다. `summary`도 execution 단위 집계이며, `case_stability`와
`stability_summary`는 고유 case 단위 집계다. case pass rate는 `combined_passed / total_runs`이고
실행 오류도 분모에 포함해 실패로 계산한다. 모든 실행 통과는 `stable_pass`, 일부만 통과하면
`flaky`, 통과가 없으면 `stable_fail`이다.

Tool 선택률은 실행마다 같은 Tool의 중복 호출을 한 번으로 계산한다. Tool confusion matrix는
expected tool을 positive, forbidden tool을 negative로 처리하며 둘 다 아닌 case와 실행 오류는
`unlabeled`로 제외한다. precision/recall 분모가 0이면 `null`이다. latency p95는 표준 라이브러리의
nearest-rank 방식(`ceil(0.95 * n)`번째 정렬값)을 사용하며, latency/token의 `null` 값은 해당 통계에서
제외한다.

baseline 비교는 `case_stability`가 있는 리포트만 지원한다. pass rate 하락, forbidden violation rate
증가, execution error rate 증가, stable pass에서 하락, flaky에서 stable fail 하락을 regression으로
표시한다. 반복 횟수가 커질수록 실제 LLM API 비용도 비례해 증가하지만 production DB와 사용자
데이터에는 접근하지 않는다.

결과는 기본적으로 `evals/reports/`에 UTF-8 JSON으로 저장된다. baseline mismatch는 Agent나
데이터셋을 개선하기 전 자연스럽게 발생할 수 있으며 기본 exit code를 실패시키지 않는다.
테스트는 scripted fake model과 빈 fake query service를 사용하므로 외부 API를 호출하지 않는다.
