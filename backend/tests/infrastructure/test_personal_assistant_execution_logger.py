import logging

from app.application.service.agent_execution_observability import (
    AgentExecutionRecord,
    AgentTerminationReason,
)
from app.infrastructure.observability.personal_assistant_execution_logger import (
    StructuredLoggingAgentExecutionRecorder,
)


def test_execution_logger_emits_structured_safe_terminal_record(caplog):
    record = AgentExecutionRecord(
        trace_id="trace-123",
        mode="health",
        termination_reason=AgentTerminationReason.COMPLETED,
        guardrail_verdict="safe",
        llm_calls=2,
        tool_rounds=1,
        tool_names=("search_health_records",),
        model_duration_ms=20,
        tool_duration_ms=5,
        execution_duration_ms=30,
        retry_attempts=1,
        provider_error_category="rate_limit",
        timeout_stage=None,
        retrieval_result_count=2,
        diary_retrieval_result_count=None,
        health_retrieval_result_count=2,
        input_tokens=3,
        output_tokens=4,
        total_tokens=7,
    )

    with caplog.at_level(logging.INFO):
        StructuredLoggingAgentExecutionRecorder().record(record)

    logged = caplog.records[0]
    assert logged.message == "personal_assistant_execution"
    assert logged.event == "personal_assistant_execution"
    assert logged.trace_id == "trace-123"
    assert logged.tool_names == ["search_health_records"]
    assert logged.retrieval_result_count == 2
    assert "PRIVATE_HEALTH_TEXT" not in caplog.text
    assert "SECRET_API_KEY" not in caplog.text
