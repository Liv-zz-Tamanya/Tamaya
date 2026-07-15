# CLOVA Tool Calling Adapter

## Decision

Tamaya keeps the existing `AiChatService` contract for current recap chat, diary generation,
finalization intent detection, and event extraction. Tool calling uses a separate
`ToolCallingChatModel` contract so the next Agent graph can bind tools without changing the
existing chat paths.

The adapter uses the official `langchain-naver` package and `ChatClovaX.bind_tools()`. This keeps
LangChain `BaseTool` objects and `AIMessage.tool_calls` in the standard LangChain format that
LangGraph `ToolNode` can consume later.

## Compatibility Notes

- Naver Cloud Platform documents Function Calling for CLOVA Studio Chat Completions v3 and
  OpenAI-compatible APIs.
- The documented Function Calling model example is `HCX-005`, which matches Tamaya's current
  `CLOVA_MODEL` default.
- The request supports `tools` and `toolChoice`; the response includes assistant `toolCalls` and
  `finishReason: tool_calls` when the model selects a tool.
- Tool result follow-up messages use role `tool` and `toolCallId`, but this PR does not execute or
  return tool results.
- NCP documentation recommends setting `maxTokens` or `maxCompletionTokens` to at least 1024 for
  Function Calling.
- Function Calling is not used with Thinking mode in this adapter.

References checked:

- NCP API documentation: <https://api.ncloud-docs.com/docs/clovastudio-chatcompletionsv3-fc>
- NCP LangChain guide: <https://guide.ncloud-docs.com/docs/clovastudio-dev-langchain>
- LangChain Naver integration: <https://docs.langchain.com/oss/python/integrations/chat/naver>
- `langchain-naver` package: <https://pypi.org/project/langchain-naver/>

## Scope

`ClovaToolCallingChatModel.ainvoke(messages, tools)` binds the provided tools, sends the LangChain
messages to CLOVA, and returns the provider `AIMessage` unchanged. Tool calls are not executed,
retried, or converted to final user text in this layer.

## Smoke Test

Run the optional smoke test manually from `backend`:

```bash
CLOVA_MOCK_MODE=false CLOVA_API_KEY=... uv run python scripts/verify_clova_tool_calling.py
```

The script sends one general prompt and one tool-seeking prompt with a harmless demo tool. It prints
content and returned `tool_calls`, but does not execute any returned tool calls.
