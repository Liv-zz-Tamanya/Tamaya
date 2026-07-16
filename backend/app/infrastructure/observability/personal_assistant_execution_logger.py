import logging

from app.application.service.agent_execution_observability import (
    AgentExecutionRecord,
)

logger = logging.getLogger(__name__)


class StructuredLoggingAgentExecutionRecorder:
    def record(self, record: AgentExecutionRecord) -> None:
        logger.info(
            "personal_assistant_execution",
            extra={
                "event": "personal_assistant_execution",
                "trace_id": record.trace_id,
                "mode": record.mode,
                "termination_reason": record.termination_reason.value,
                "guardrail_verdict": record.guardrail_verdict,
                "llm_calls": record.llm_calls,
                "tool_rounds": record.tool_rounds,
                "tool_names": list(record.tool_names),
                "model_duration_ms": record.model_duration_ms,
                "tool_duration_ms": record.tool_duration_ms,
                "execution_duration_ms": record.execution_duration_ms,
                "retry_attempts": record.retry_attempts,
                "provider_error_category": record.provider_error_category,
                "timeout_stage": record.timeout_stage,
                "retrieval_result_count": record.retrieval_result_count,
                "diary_retrieval_result_count": record.diary_retrieval_result_count,
                "health_retrieval_result_count": record.health_retrieval_result_count,
                "input_tokens": record.input_tokens,
                "output_tokens": record.output_tokens,
                "total_tokens": record.total_tokens,
            },
        )
