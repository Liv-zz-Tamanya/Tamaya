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

실제 실행 결과에서 도구 호출 이름은 하위 호환 필드인 `actual_tools`로 확인할 수 있다.
상세 분석이 필요하면 `tool_calls`와 `llm_call_traces`에서 모델이 생성한 Tool Call arguments,
finish reason, 호출별 token/duration, 최종 응답을 확인한다.

## 파일과 데이터 수

- `datasets/diary_cases.jsonl`: 14개
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

## Observability fields

평가 runner는 Agent 실행 recorder를 `full` trace mode로 사용한다. JSON report의 기존 필드는 유지하며
case 실행마다 다음 상세 필드를 추가로 저장한다.

- `tool_calls`: LLM이 생성한 Tool Call의 `round`, `call_id`, `name`, 정규화된 JSON `arguments`.
- `llm_call_traces`: LLM 호출 순번별 `finish_reason`, 응답 content, 호출에 포함된 Tool Call, token usage, duration.
- `first_finish_reason`, `first_response_content`, `final_response_content`: 첫 모델 응답과 최종 응답을 빠르게 확인하기 위한 요약.
- `model_config`: provider, model, temperature, max tokens, timeout, 그리고 지원하지 않는 `top_p`, `seed`, `parallel_tool_calls`의 `null` 값.
- `prompt_metadata`: system prompt와 tool schema의 canonical JSON 기반 sha256 hash, git commit, dirty 여부.

Tool 결과 본문은 report에 저장하지 않는다. 기본 production recorder는 `basic` trace mode라 Tool arguments와
LLM response content를 비워 민감한 Diary/Health 원문이 운영 로그에 남지 않게 한다.

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

## 평가 전용 DB fixture (RAG 평가 기반)

`fixtures/`는 RAG 평가(retrieval·chunk·E2E)를 위한 합성 데이터다. 실제 사용자
데이터가 아니며, 운영 DB와 분리된 평가 전용 DB(`settings.eval_database_url`,
기본 `aidiary_eval`)에만 시드된다.

- `fixtures/virtual_users.json`: 가상 사용자 3명. device_id는 반드시 `eval-` 접두사.
  건강 데이터가 전혀 없는 사용자 1명 포함(빈 검색 케이스용).
- `fixtures/diary_fixtures.jsonl`: 하루치 일기 대화 + 그 대화에서 추출되어야 할
  정답 Event Chunk(`gold_chunks`). chunk 형식은 `CHUNK_EXTRACT_USER_REQUEST`가
  규정하는 text/tags/event_type/who/where/when 계약을 따른다. gold chunk는 시드 시
  `event_chunks` 행이 되고, retrieval 평가의 정답 문서이자 chunk 생성 평가(PR3)의
  정답 레이블로 재사용된다.
- `fixtures/health_fixtures.jsonl`: 하루치 건강 chunk. text는 `HealthChunkBuilder`가
  생성하는 한국어 자연어 형식을 따른다.
- 사용자 간 유출·hard negative 검사를 위해 서로 다른 사용자에 유사 사건이 의도적으로
  들어 있다(예: 하나/소라의 "성수동 카페").

검증과 시드:

```bash
uv run python -m evals.validate_fixtures      # 파일 계약 검사 (DB 접근 없음)
uv run python -m evals.seed_fixtures          # 시드 — 이미 있는 행은 skip
uv run python -m evals.seed_fixtures --reset  # eval 데이터 삭제 후 재시드
uv run python -m evals.seed_fixtures --reset-only
```

안전장치: 대상 DB명이 운영 `database_url`과 같거나 이름에 `eval`이 없으면 시드가
거부된다. reset은 fixture의 `eval-` 접두사 device_id 스코프만 삭제한다. 모든 행 id는
`uuid5`로 결정론 생성되어 재실행해도 중복 삽입되지 않는다. 임베딩은 프로덕션과 동일한
로컬 sentence-transformers 모델을 사용한다(외부 API·비용 없음). database가 없으면
자동 생성하고 `CREATE EXTENSION vector` 후 스키마를 만든다.

## Retrieval 검색 평가

Agent를 제외하고 검색 service(`DiaryMemoryQueryService`, `HealthRecordQueryService`)를
직접 호출해 순위 품질을 잰다. LLM 호출이 없고 임베딩은 로컬 모델이므로 비용이 없다.
전제: 평가 DB에 fixture가 시드되어 있어야 한다.

```bash
uv run python -m evals.validate_retrieval_dataset   # 데이터셋·fixture 참조 검증
uv run python -m evals.run_retrieval_evaluation
uv run python -m evals.run_retrieval_evaluation --case-id ret-diary-001
uv run python -m evals.run_retrieval_evaluation \
  --baseline evals/baselines/retrieval-baseline.json --fail-on-regression
```

- 지표: Hit@1·3·5, Precision@k, Recall@k, MRR(k=`--top-k`, 기본 5). 빈 정답
  케이스(`empty_retrieval`)는 순위 지표에서 제외하고 "결과 0건" 여부만 검사한다.
- 검색 결과 UUID는 uuid5 역매핑으로 fixture chunk 라벨로 복원된다. 다른 사용자
  소유 chunk가 나오면 `leaked_labels`(사용자 간 유출), fixture에 없는 행이 나오면
  `unknown_ids`로 잡힌다 — 두 카운트는 항상 0이어야 정상이다.
- category: `direct_recall`, `paraphrase_recall`, `multi_relevant`, `hard_negative`,
  `cross_user_probe`, `date_reference`(알려진 약점 정량화), `empty_retrieval`.
- baseline: `evals/baselines/retrieval-baseline.json`(git 추적). 임베딩이 결정론적이라
  같은 코드·데이터에서 결과가 완전히 재현되며, `--fail-on-regression`으로 회귀를
  잡는다. 개선 후에는 새 리포트로 baseline 파일을 교체한다.

## Event Chunk 생성 평가

diary fixture의 대화를 실제 CLOVA chunk 추출(`extract_event_chunks`)에 넣고 gold
chunk와 대조한다. **CLOVA 호출 비용이 발생한다**(fixture 12건 × repeat). DB는 쓰지
않는다. 검색 실패가 chunk 생성 문제인지 retriever 문제인지는 이 리포트와 retrieval
리포트를 대조해 분리한다.

```bash
uv run python -m evals.run_chunk_evaluation
uv run python -m evals.run_chunk_evaluation --fixture-id diary-hana-0602 --repeat 3
uv run python -m evals.run_chunk_evaluation --threshold 0.6
```

- 매칭: 문자열이 아니라 **임베딩 cosine 유사도 greedy 1:1**. 같은 사건의 패러프레이즈를
  매칭하기 위함이다. 기본 threshold 0.55는 MiniLM 보정 결과다(0.65는 동일 사건
  패러프레이즈 과반을 환각으로 오판). 임베딩 교체 시 재보정 필요.
- 지표: 사건 Recall(누락), Precision, 병합 의심(누락인데 다른 추출문에 흡수),
  과분할(매칭된 정답의 중복 추출), 환각 의심(근거 없는 추출), 계약 위반 행,
  metadata(event_type/who/where/when) 정확도. who/where/when은 양쪽 null이면 "언급
  없음 계약 준수"로 정답, 표기 차이는 포함 관계로 흡수한다.
- 매처 자체가 임베딩 품질에 의존하므로 누락·환각 목록에는 best_similarity와 원문을
  남긴다 — 임계 근처(0.4~0.55) 항목은 사람이 확인할 것.
- 프롬프트는 `chunk_extraction_prompt` 모듈로 분리되어 리포트의 `prompt_hash`로
  버전 추적된다.

## RAG 답변 생성 평가

검색을 우회하고 정답 문서(fixture chunk)를 프로덕션 tool 결과 wire 형식 그대로
컨텍스트에 주입해, "문서가 주어졌을 때 제대로 답하는가"만 격리 측정한다.
**CLOVA 비용 발생**(케이스당 생성 1회 + judge 1회). DB 미사용.

```bash
uv run python -m evals.run_generation_evaluation
uv run python -m evals.run_generation_evaluation --case-id gen-health-201 --repeat 3
```

- category: `grounded_recall`·`multi_doc_summary`(완전성 채점), `unsupported_bait`
  (문서에 없는 걸 물어 지어내는지), `no_record_abstention`(빈 검색 결과 — 기록 없다고
  답해야 통과), `health_boundary`(진단·처방 확장 금지).
- 결정론 검사: expected_facts 완전성(공백 정규화 + 동의 표현 대안), 처방 토큰
  (`medical_guardrail.contains_prescriptive_content`).
- LLM judge: unsupported claim·abstention·진단/처방 판정. **현재 judge는 생성 모델과
  같은 CLOVA라 자기 채점 편향이 있고, 공감·되묻기를 unsupported로 과잉 판정하는
  경향이 실측됨** — faithful rate는 참고 지표로 보고 판정 원문(리포트의 raw_response)을
  사람이 확인할 것. 외부 judge 도입은 PR8에서.
- 주의: 프로덕션 input guardrail을 의도적으로 우회한다 — guardrail이 뚫렸을 때 생성
  모델이 마지막 방어선이 되는지 측정하는 평가다(defense in depth).
- 문서를 주었는데 다시 tool을 호출하려 하면 `re_search`로 기록된다.

## End-to-End Agent RAG 평가

사용자 입력 → tool 선택 → query 생성 → 검색(평가 DB) → 최종 답변까지 프로덕션
agent 조립 경로 전체를 실행한다. **CLOVA 비용 발생**(agent 실행 + judge). 전제:
평가 DB 시드 완료.

```bash
uv run python -m evals.run_e2e_evaluation
uv run python -m evals.run_e2e_evaluation --case-id e2e-diary-001 --repeat 3
```

- 실행마다 **첫 실패 단계 하나**로 분류된다(파이프라인 순서):
  `EXECUTION_ERROR` → `GUARDRAIL_BLOCKED` → `TOOL_OVER_CALL`/`TOOL_UNDER_CALL`/
  `WRONG_TOOL` → `CROSS_USER_LEAK` → `RETRIEVAL_MISS`/`RETRIEVAL_PARTIAL` →
  `ABSTENTION_FAIL` → `UNSUPPORTED_CLAIM` → `INCOMPLETE_ANSWER` → `PASS`
- 검색 service를 recording wrapper로 감싸 **모델이 생성한 query 문자열과 검색된
  문서 id**를 기록한다 — query 생성 품질과 retrieval 실패를 케이스별로 추적 가능.
- 답변 채점은 generation 평가와 동일(완전성 결정론 + judge). judge 과잉 판정
  한계도 동일하게 적용되므로 `UNSUPPORTED_CLAIM` 판정은 원문을 확인할 것.
- 토큰·지연(mean/p50/p95)·반복 안정성(stable/flaky) 집계 포함.

## 일기 생성 품질 평가

diary fixture의 대화를 실제 CLOVA `generate_diary`에 넣어 제목·본문·감정·키워드
변환 품질을 잰다. **CLOVA 비용 발생**(12건 × repeat). DB 미사용.

```bash
uv run python -m evals.run_diary_generation_evaluation
uv run python -m evals.run_diary_generation_evaluation --fixture-id diary-hana-0602 --repeat 3
```

- 핵심 사건 반영: gold chunk ↔ 본문 문장 임베딩 매칭(threshold는 chunk 평가와 동일).
- 문장 단위 grounding: 각 본문 문장을 gold chunk/사용자 발화/assistant 발화와 대조 —
  `ungrounded`(원문에 없는 문장 의심), `assistant_only`(assistant 발화에만 근거한
  발화 혼동 의심)로 분류한다. **감상·다짐 문장이 ungrounded로 잡히는 경향이 있으므로
  카운트만 보지 말고 리포트의 문장·유사도를 사람이 확인할 것.**
- 계약 검사(결정론): JSON 스키마, emotion 어휘(DIARY_EMOTIONS), satisfaction 0~100,
  keywords 2~3개, 문장 수 4~5, 일반어 키워드(오늘/기분/생각/하루) 금지.
- 감정 타당성: fixture의 `plausible_emotions` 라벨과 대조(라벨은 사람이 작성).
- 키워드 근거: 토큰 단위 검사 — 명사구 합성("항공권 예매")은 허용하고, 어느 토큰도
  원문에 없는 키워드만 미근거로 판정.

## 코칭 정성신호 추출 평가

코칭 대화 fixture(`fixtures/coaching_fixtures.jsonl`, DB 시드 안 함)를 실제 CLOVA
`extract_signal`에 넣어 감정·행동·polarity 추출을 gold 라벨과 대조한다 — 주간·월간
Insight 원천 데이터 품질 검증. **CLOVA 비용 발생**(10건 × repeat).

```bash
uv run python -m evals.run_signal_evaluation
uv run python -m evals.run_signal_evaluation --fixture-id coaching-hana-01 --repeat 3
```

- behavior 매칭: gold의 surface_forms(표기 대안)와 정규화 포함 관계, greedy 1:1 →
  micro Precision/Recall/F1. 매칭된 쌍에서 polarity(±1) 정확도.
- 환각(존재하지 않는 행동): 어느 gold와도 매칭 안 된 추출 행동. fixture에는
  "하고 싶었는데 못 함"(소망)류 함정과 gold_behaviors가 빈 케이스(빈 배열 계약)가
  포함되어 있다.
- 감정: fixture의 plausible_emotions(사람 작성)와 대조. 어휘는 DIARY_EMOTIONS와 동일.
- 클라이언트가 파싱 실패를 None으로 흡수하는 프로덕션 동작은 extraction_none으로
  분리 집계된다(전 gold 미검출로 recall에 반영).
