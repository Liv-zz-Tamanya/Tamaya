"""주간 인사이트 리포트 생성 usecase — 캐시 우선, 결정론 선정, LLM 최소 호출.

실행 순서(고정):
캐시 조회 → facts·기준선 → 결정론 요약 → 통계 평가 → 최근 노출 조회 →
후보 선정 → (비생성 상태는 LLM 없이 저장) → context 조립 → INSIGHT Agent →
output 검사·파싱 → 저장.

비용 경계: 캐시 hit·INSUFFICIENT_DATA·NO_SIGNAL·COOLDOWN에서는 LLM을
호출하지 않는다. 같은 주차 재호출은 항상 기존 리포트를 반환한다(재생성 없음).
"""

from collections.abc import Callable
from datetime import datetime, timedelta
from uuid import uuid4

from app.application.service.insight_generation_prompt import (
    InsightGenerationContext,
    insight_prompt_hash,
)
from app.application.service.insight_output_parser import parse_insight_cards
from app.application.service.insight_statistics import evaluate_hypotheses
from app.application.usecase.insight_facts import load_analysis_facts
from app.application.usecase.personal_assistant_agent import (
    INSIGHT_SAFETY_BLOCKED_MESSAGE_ID,
    PersonalAssistantMode,
)
from app.application.usecase.personal_assistant_agent_factory import PersonalAssistantAgentFactory
from app.domain.model.insight_report import (
    InsightCard,
    InsightPeriodType,
    InsightReport,
    InsightReportStatus,
)
from app.domain.model.medical_visit import MedicalVisit
from app.domain.repository.diary_repository import DiaryRepository
from app.domain.repository.health_record_repository import HealthRecordRepository
from app.domain.repository.insight_report_repository import InsightReportRepository
from app.domain.repository.medical_visit_repository import MedicalVisitRepository
from app.domain.repository.sleep_record_repository import SleepRecordRepository
from app.domain.service.insight_hypotheses import REGISTERED_HYPOTHESES, StatisticalFinding
from app.domain.service.insight_models import DailyFact
from app.domain.service.insight_period import week_bounds
from app.domain.service.insight_selection import (
    INSIGHT_HYPOTHESIS_COOLDOWN_DAYS,
    MAX_INSIGHT_CARDS,
    InsightSelectionOutcome,
    select_evidence_dates,
    select_insight_candidates,
)
from app.domain.service.wellbeing_score import compute_wellbeing

PAYLOAD_SCHEMA_VERSION = 1

_OUTCOME_TO_STATUS = {
    InsightSelectionOutcome.INSUFFICIENT_DATA: InsightReportStatus.INSUFFICIENT_DATA,
    InsightSelectionOutcome.NO_SIGNAL: InsightReportStatus.NO_SIGNAL,
    InsightSelectionOutcome.COOLDOWN: InsightReportStatus.COOLDOWN,
}


class GetCachedWeeklyInsightReportUseCase:
    def __init__(self, report_repo: InsightReportRepository) -> None:
        self._report_repo = report_repo

    async def execute(self, device_id: str, year: int, week: int) -> InsightReport | None:
        return await self._report_repo.find_by_period(
            device_id, InsightPeriodType.WEEKLY, f"{year}-W{week:02d}"
        )


class GenerateWeeklyInsightReportUseCase:
    def __init__(
        self,
        report_repo: InsightReportRepository,
        health_repo: HealthRecordRepository,
        sleep_repo: SleepRecordRepository,
        diary_repo: DiaryRepository,
        visit_repo: MedicalVisitRepository,
        agent_factory: PersonalAssistantAgentFactory,
        model_name: str | None = None,
        clock: Callable[[], datetime] = datetime.now,
    ) -> None:
        self._report_repo = report_repo
        self._health_repo = health_repo
        self._sleep_repo = sleep_repo
        self._diary_repo = diary_repo
        self._visit_repo = visit_repo
        self._agent_factory = agent_factory
        self._model_name = model_name
        self._clock = clock  # 시간 의존 테스트를 위해 한 곳에서만 주입

    async def execute(self, device_id: str, year: int, week: int) -> tuple[InsightReport, bool]:
        """(리포트, from_cache)를 반환한다."""
        period_key = f"{year}-W{week:02d}"
        cached = await self._report_repo.find_by_period(
            device_id, InsightPeriodType.WEEKLY, period_key
        )
        if cached is not None:
            return cached, True

        start, end = week_bounds(year, week)
        # 통계·근거 탐색은 주간 조각(n<20)이 아니라 최근 90일 분석 창에서 수행한다
        period_facts, analysis_facts, baselines = await load_analysis_facts(
            self._health_repo, self._sleep_repo, self._diary_repo, self._visit_repo,
            device_id, start, end,
        )
        window_start = analysis_facts[0].date
        wellbeing = compute_wellbeing(period_facts, baselines)
        visits = await self._visit_repo.find_by_date_range(device_id, window_start, end)
        now = self._clock()

        findings = evaluate_hypotheses(analysis_facts)
        recent_reports = await self._report_repo.find_recent(
            device_id, now - timedelta(days=INSIGHT_HYPOTHESIS_COOLDOWN_DAYS)
        )
        exposed_keys = {
            card.hypothesis_key
            for report in recent_reports
            if report.status == InsightReportStatus.GENERATED
            for card in report.cards
        }
        selection = select_insight_candidates(findings, exposed_keys)

        period_summary = _build_period_summary(
            period_key, start, end, window_start, wellbeing, analysis_facts, visits
        )
        verified_payload = tuple(_finding_payload(f) for f in findings)
        report_id = uuid4()

        if selection.outcome != InsightSelectionOutcome.SELECTED:
            report = self._build_report(
                report_id=report_id,
                device_id=device_id,
                period_key=period_key,
                status=_OUTCOME_TO_STATUS[selection.outcome],
                cards=(),
                selected_keys=(),
                period_summary=period_summary,
                verified_payload=verified_payload,
                selected_payload=(),
                now=now,
            )
            saved = await self._report_repo.save(report)
            return saved, saved.id != report_id

        hypothesis_by_key = {h.key: h for h in REGISTERED_HYPOTHESES}
        selected_keys = tuple(f.hypothesis_key for f in selection.selected)
        evidence_by_key = {
            f.hypothesis_key: select_evidence_dates(
                hypothesis_by_key[f.hypothesis_key], analysis_facts, f.effect_size
            )
            for f in selection.selected
        }
        allowed_dates = tuple(sorted({d for dates in evidence_by_key.values() for d in dates}))
        selected_payload = tuple(
            {
                **_finding_payload(f),
                "evidence_dates": [d.isoformat() for d in evidence_by_key[f.hypothesis_key]],
            }
            for f in selection.selected
        )
        # context의 start/end는 분석 창 — 근거 날짜·tool 조회 범위의 기준이다
        context = InsightGenerationContext(
            generation_run_id=report_id,
            period_type=InsightPeriodType.WEEKLY,
            period_key=period_key,
            start_date=window_start,
            end_date=end,
            period_summary=period_summary,
            verified_candidates=verified_payload,
            selected_candidates=selected_payload,
            allowed_evidence_dates=allowed_dates,
        )

        agent = self._agent_factory.create_for_insight(
            device_id=device_id,
            run_id=report_id,
            context=context,
            day_facts_by_date={fact.date: fact for fact in analysis_facts},
            medical_visits=visits,
        )
        response = await agent.run(
            messages=[],  # 사용자 메시지 없음 — 가짜 HumanMessage 금지
            mode=PersonalAssistantMode.INSIGHT,
            insight_context=context,
            execution_ref=str(report_id),
        )

        if response.id == INSIGHT_SAFETY_BLOCKED_MESSAGE_ID:
            # 위험 원문은 카드·payload 어디에도 저장하지 않는다
            report = self._build_report(
                report_id=report_id,
                device_id=device_id,
                period_key=period_key,
                status=InsightReportStatus.SAFETY_BLOCKED,
                cards=(),
                selected_keys=selected_keys,
                period_summary=period_summary,
                verified_payload=verified_payload,
                selected_payload=selected_payload,
                now=now,
            )
            saved = await self._report_repo.save(report)
            return saved, saved.id != report_id

        cards = parse_insight_cards(  # 계약 위반이면 InsightOutputError — 저장하지 않는다
            _message_text(response),
            selected_hypothesis_keys=selected_keys,
            allowed_evidence_dates=allowed_dates,
            period_start=window_start,
            period_end=end,
            max_cards=MAX_INSIGHT_CARDS,
        )
        report = self._build_report(
            report_id=report_id,
            device_id=device_id,
            period_key=period_key,
            status=InsightReportStatus.GENERATED,
            cards=cards,
            selected_keys=selected_keys,
            period_summary=period_summary,
            verified_payload=verified_payload,
            selected_payload=selected_payload,
            now=now,
        )
        saved = await self._report_repo.save(report)
        return saved, saved.id != report_id

    def _build_report(
        self,
        *,
        report_id,
        device_id: str,
        period_key: str,
        status: InsightReportStatus,
        cards: tuple[InsightCard, ...],
        selected_keys: tuple[str, ...],
        period_summary: dict,
        verified_payload: tuple[dict, ...],
        selected_payload: tuple[dict, ...],
        now: datetime,
    ) -> InsightReport:
        payload = {
            "schema_version": PAYLOAD_SCHEMA_VERSION,
            "status": status.value,
            "period_summary": period_summary,
            "verified_candidates": list(verified_payload),
            "selected_candidates": list(selected_payload),
            "cards": [
                {
                    "hypothesis_key": card.hypothesis_key,
                    "title": card.title,
                    "message": card.message,
                    "evidence_dates": [d.isoformat() for d in card.evidence_dates],
                }
                for card in cards
            ],
        }
        model_meta = {
            "generation_run_id": str(report_id),
            "mode": PersonalAssistantMode.INSIGHT.value,
            "prompt_hash": insight_prompt_hash(),
            "model": self._model_name,  # 설정 주입 — 하드코딩 금지
            "selected_hypothesis_keys": list(selected_keys),
        }
        return InsightReport(
            id=report_id,
            device_id=device_id,
            period_type=InsightPeriodType.WEEKLY,
            period_key=period_key,
            status=status,
            cards=cards,
            selected_hypothesis_keys=selected_keys,
            payload=payload,
            model_meta=model_meta,
            created_at=now,
            updated_at=now,
        )


def _build_period_summary(
    period_key: str,
    start,
    end,
    window_start,
    wellbeing,
    analysis_facts: list[DailyFact],
    visits: list[MedicalVisit],
) -> dict:
    # 결정론 코드가 계산한 값만 — None은 null 그대로, coverage를 숨기지 않는다.
    # wellbeing은 주간, 관측 일수·진료는 통계와 같은 분석 창 기준이다.
    return {
        "period": period_key,
        "start_date": start.isoformat(),
        "end_date": end.isoformat(),
        "analysis_window_start": window_start.isoformat(),
        "analysis_window_end": end.isoformat(),
        "wellbeing_score": wellbeing.score,
        "emotion_score": wellbeing.emotion_score,
        "behavior_score": wellbeing.behavior_score,
        "diary_days": wellbeing.diary_days,
        "lifelog_days": wellbeing.lifelog_days,
        "sleep_observed_days": sum(f.sleep_minutes is not None for f in analysis_facts),
        "steps_observed_days": sum(f.steps is not None for f in analysis_facts),
        "medical_visit_count": sum(start <= v.visit_date <= end for v in visits),
        "analysis_window_medical_visit_count": len(visits),
    }


def _finding_payload(finding: StatisticalFinding) -> dict:
    return {
        "hypothesis_key": finding.hypothesis_key,
        "test_type": finding.test_type.value,
        "n": finding.n,
        "effect_size": finding.effect_size,
        "p_value": finding.p_value,
        "q_value": finding.q_value,
        "gate_passed": finding.gate_passed,
        "coverage": {
            "eligible_days": finding.coverage.eligible_days,
            "paired_days": finding.coverage.paired_days,
            "predictor_observed_days": finding.coverage.predictor_observed_days,
            "outcome_observed_days": finding.coverage.outcome_observed_days,
        },
        "failure_reasons": [reason.value for reason in finding.failure_reasons],
    }


def _message_text(message) -> str:
    content = message.content
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return "".join(
            block if isinstance(block, str) else str(block.get("text", ""))
            for block in content
        )
    raise TypeError("unsupported agent message content")
