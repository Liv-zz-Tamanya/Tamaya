import uuid
from datetime import date
from uuid import UUID

from app.application.service.ai_chat_service import AiChatService
from app.application.service.embedding_service import EmbeddingService
from app.domain.model.chat_message import ChatMessage
from app.domain.model.event_chunk import EventChunk
from app.domain.repository.event_chunk_repository import EventChunkRepository


class ExtractChunksUseCase:
    def __init__(
        self,
        ai: AiChatService,
        embedding_service: EmbeddingService,
        event_chunk_repo: EventChunkRepository,
    ) -> None:
        self._ai = ai
        self._embedding_service = embedding_service
        self._event_chunk_repo = event_chunk_repo

    async def execute(
        self,
        session_id: UUID,
        diary_date: date,
        messages: list[ChatMessage],
    ) -> None:
        chunks_data = await self._ai.extract_event_chunks(messages)
        if not chunks_data:
            return

        texts = [c["text"] for c in chunks_data]
        embeddings = self._embedding_service.embed(texts)

        chunks = [
            EventChunk(
                id=uuid.uuid4(),
                chat_session_id=session_id,
                diary_date=diary_date,
                text=chunks_data[i]["text"],
                embedding=embeddings[i],
                tags=chunks_data[i].get("tags", []),
                event_type=chunks_data[i].get("event_type", "personal"),
                who=chunks_data[i].get("who") or None,
                where=chunks_data[i].get("where") or None,
                when=chunks_data[i].get("when") or None,
            )
            for i in range(len(chunks_data))
        ]
        await self._event_chunk_repo.save_all(chunks)
