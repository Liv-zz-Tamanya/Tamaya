"""평가 케이스 로딩·선택과 LangChain 메시지 변환."""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from pathlib import Path

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage

from evals.schemas import PersonalAssistantEvalCase
from evals.validate_dataset import DATASET_FILENAMES


def messages_for_case(case: PersonalAssistantEvalCase) -> list[BaseMessage]:
    messages: list[BaseMessage] = []
    for item in case.history:
        if item.role == "user":
            messages.append(HumanMessage(content=item.content))
        elif item.role == "assistant":
            messages.append(AIMessage(content=item.content))
        else:
            raise ValueError(f"case {case.id}: unsupported history role: {item.role}")
    messages.append(HumanMessage(content=case.input))
    return messages


def load_cases(dataset_dir: Path, datasets: Sequence[str] | None = None) -> list[tuple[str, PersonalAssistantEvalCase]]:
    selected = set(datasets or dataset_names())
    loaded: list[tuple[str, PersonalAssistantEvalCase]] = []
    for filename in DATASET_FILENAMES:
        name = filename.removesuffix("_cases.jsonl")
        if name not in selected:
            continue
        path = dataset_dir / filename
        for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            if not line.strip():
                raise ValueError(f"{path}:{line_number}: empty JSONL row")
            loaded.append((name, PersonalAssistantEvalCase.model_validate_json(line)))
    return loaded


def dataset_names() -> list[str]:
    return [filename.removesuffix("_cases.jsonl") for filename in DATASET_FILENAMES]


def select_cases(
    cases: Iterable[tuple[str, PersonalAssistantEvalCase]], case_id: str | None, limit: int | None
) -> list[tuple[str, PersonalAssistantEvalCase]]:
    selected = [(dataset, case) for dataset, case in cases if case_id is None or case.id == case_id]
    if case_id is not None and not selected:
        raise ValueError(f"case not found: {case_id}")
    return selected[:limit] if limit is not None else selected
