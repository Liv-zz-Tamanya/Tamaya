from __future__ import annotations

import asyncio
import sys
from pathlib import Path

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.tools import StructuredTool
from pydantic import BaseModel, Field

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.infrastructure.config.settings import settings
from app.infrastructure.external.clova_tool_calling import ClovaToolCallingChatModel


class LookupInput(BaseModel):
    query: str = Field(description="A harmless lookup query.")


async def _lookup_demo(query: str) -> dict:
    return {"query": query, "note": "This function is not executed by the smoke test."}


def _demo_tool() -> StructuredTool:
    return StructuredTool.from_function(
        coroutine=_lookup_demo,
        name="lookup_demo",
        description="Look up harmless demo information when the user explicitly asks to search.",
        args_schema=LookupInput,
    )


async def main() -> None:
    if settings.clova_mock_mode or not settings.clova_api_key:
        print(
            "Skipping CLOVA tool-calling smoke test: set CLOVA_MOCK_MODE=false and CLOVA_API_KEY."
        )
        return

    model = ClovaToolCallingChatModel()
    messages = [
        SystemMessage(content="You are a concise assistant."),
        HumanMessage(content="오늘 기분이 좀 복잡해."),
    ]
    text_response = await model.ainvoke(messages, [_demo_tool()])
    print("General response content:", text_response.content)
    print("General response tool_calls:", text_response.tool_calls)

    tool_response = await model.ainvoke(
        [
            SystemMessage(content="Use tools when lookup is needed."),
            HumanMessage(content="lookup_demo 도구로 어제 발표 기록을 찾아줘."),
        ],
        [_demo_tool()],
    )
    print("Tool response content:", tool_response.content)
    print("Tool response tool_calls:", tool_response.tool_calls)
    print("The smoke test does not execute returned tool calls.")


if __name__ == "__main__":
    asyncio.run(main())
