"""
Chat API — SSE streaming chat with AI.

POST /chat/message  — Send message, receive SSE stream
GET  /chat/sessions — List user's chat sessions
GET  /chat/sessions/{id}/messages — Get session messages
"""

import json
import uuid

import structlog
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from riskcast.api.deps import get_company_id, get_db, get_user_id
from riskcast.config import settings
from riskcast.db import queries as db_queries
from riskcast.schemas.chat import (
    ChatMessageRequest,
    MessageResponse,
    SessionListResponse,
    SessionResponse,
)
from riskcast.services.context_builder import ContextBuilder
from riskcast.services.llm_gateway import LLMGateway
from riskcast.services.omen_client import OmenClient
from riskcast.services.suggestion_extractor import SuggestionExtractor

logger = structlog.get_logger(__name__)
router = APIRouter(prefix="/api/v1/chat", tags=["chat"])

# Service singletons (initialized once, reused)
_llm = LLMGateway()
_omen = OmenClient(base_url=settings.omen_url)
_context_builder = ContextBuilder(llm=_llm, omen_client=_omen)
_suggestion_extractor = SuggestionExtractor()


@router.post("/message")
async def send_message(
    body: ChatMessageRequest,
    db: AsyncSession = Depends(get_db),
    company_id: uuid.UUID = Depends(get_company_id),
    user_id: uuid.UUID = Depends(get_user_id),
):
    """
    Send a chat message and receive an SSE stream response.

    Events:
    - type: chunk   — partial AI text
    - type: done    — final clean text + suggestions
    - type: error   — error message
    """
    cid = str(company_id)
    uid = str(user_id)

    # Get or create session
    chat_session = await db_queries.get_or_create_session(
        db, cid, uid, str(body.session_id) if body.session_id else None
    )
    session_id = str(chat_session.id)

    # Save user message
    await db_queries.save_message(db, session_id, cid, "user", body.message)
    await db.commit()

    # Build context
    history_rows = await db_queries.get_session_messages(db, session_id, limit=10)
    history = [{"role": m.role, "content": m.content} for m in history_rows]

    context = await _context_builder.build(
        session=db,
        company_id=cid,
        user_query=body.message,
        session_history=history,
    )

    async def generate():
        full_response = ""

        try:
            async for chunk in _llm.stream(
                system_prompt=context.system_prompt,
                user_message=body.message,
            ):
                full_response += chunk
                yield f"data: {json.dumps({'type': 'chunk', 'content': chunk}, ensure_ascii=False)}\n\n"

        except Exception as e:
            logger.error("llm_stream_error", error=str(e))
            error_msg = (
                "Phản hồi bị gián đoạn do lỗi hệ thống. Dữ liệu trên có thể chưa đầy đủ."
                if full_response
                else "Xin lỗi, hệ thống đang quá tải. Vui lòng thử lại sau giây lát."
            )
            yield f"data: {json.dumps({'type': 'error', 'message': error_msg}, ensure_ascii=False)}\n\n"
            return

        # Save assistant response
        from riskcast.db.engine import get_session_factory

        factory = get_session_factory()
        async with factory() as save_session:
            # SET tenant context for PostgreSQL RLS (skip on SQLite)
            if "postgresql" in settings.async_database_url:
                from sqlalchemy import text
                await save_session.execute(
                    text("SET LOCAL app.current_company_id = :cid"),
                    {"cid": cid},
                )

            msg = await db_queries.save_message(
                save_session,
                session_id,
                cid,
                "assistant",
                full_response,
                context_used={
                    "signals_count": len(context.signals_summary),
                    "data_keys": list(context.data_summary.keys()),
                    "intent_method": context.intent.get("method", "unknown"),
                    "intent_type": context.intent.get("type", "unknown"),
                },
            )

            # Extract suggestions
            suggestions = await _suggestion_extractor.extract_and_save(
                session=save_session,
                company_id=cid,
                message_id=str(msg.id),
                ai_response=full_response,
            )

            await save_session.commit()

        # Send final clean response + suggestions
        clean = _suggestion_extractor.clean_response(full_response)
        yield f"data: {json.dumps({'type': 'done', 'session_id': session_id, 'clean_content': clean, 'suggestions': suggestions}, ensure_ascii=False)}\n\n"

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.get("/sessions", response_model=SessionListResponse)
async def list_sessions(
    db: AsyncSession = Depends(get_db),
    company_id: uuid.UUID = Depends(get_company_id),
    user_id: uuid.UUID = Depends(get_user_id),
):
    """List chat sessions for the current user."""
    sessions = await db_queries.get_user_sessions(
        db, str(company_id), str(user_id)
    )
    return SessionListResponse(
        sessions=[SessionResponse.model_validate(s) for s in sessions]
    )


@router.get("/sessions/{session_id}/messages", response_model=list[MessageResponse])
async def get_messages(
    session_id: uuid.UUID,
    limit: int = Query(default=50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    company_id: uuid.UUID = Depends(get_company_id),
):
    """Get messages for a chat session."""
    messages = await db_queries.get_session_messages(db, str(session_id), limit=limit)
    if not messages:
        raise HTTPException(status_code=404, detail="Session not found or empty")
    return [MessageResponse.model_validate(m) for m in messages]
