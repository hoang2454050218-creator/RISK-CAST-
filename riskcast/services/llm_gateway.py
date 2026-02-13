"""
LLM Gateway — Claude API integration.

Single provider (Anthropic) to reduce complexity.
- Claude Sonnet: chat responses (streaming)
- Claude Haiku: intent classification (fast, cheap)
"""

from typing import AsyncGenerator

import httpx
import structlog

from riskcast.config import settings

logger = structlog.get_logger(__name__)

# Anthropic API constants
ANTHROPIC_API_URL = "https://api.anthropic.com/v1/messages"
ANTHROPIC_VERSION = "2023-06-01"


class LLMGateway:
    """Gateway for Claude API — streaming and non-streaming."""

    def __init__(self, api_key: str | None = None):
        self.api_key = api_key or settings.anthropic_api_key
        if not self.api_key:
            logger.warning("anthropic_api_key_missing", msg="LLM features will be unavailable")

    async def stream(
        self,
        system_prompt: str,
        user_message: str,
        model: str = "claude-sonnet-4-20250514",
        max_tokens: int = 2048,
    ) -> AsyncGenerator[str, None]:
        """
        Stream a response from Claude.

        Yields text chunks as they arrive.
        Raises on API errors after yielding what we have.
        """
        if not self.api_key:
            yield "Xin lỗi, hệ thống AI chưa được cấu hình. Vui lòng liên hệ admin."
            return

        headers = {
            "x-api-key": self.api_key,
            "anthropic-version": ANTHROPIC_VERSION,
            "content-type": "application/json",
        }

        payload = {
            "model": model,
            "max_tokens": max_tokens,
            "system": system_prompt,
            "messages": [{"role": "user", "content": user_message}],
            "stream": True,
        }

        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                async with client.stream(
                    "POST", ANTHROPIC_API_URL, json=payload, headers=headers
                ) as response:
                    if response.status_code != 200:
                        error_body = await response.aread()
                        logger.error(
                            "llm_api_error",
                            status=response.status_code,
                            body=error_body.decode()[:500],
                        )
                        yield "Xin lỗi, hệ thống đang gặp sự cố. Vui lòng thử lại sau."
                        return

                    async for line in response.aiter_lines():
                        if not line.startswith("data: "):
                            continue

                        data = line[6:]
                        if data == "[DONE]":
                            break

                        try:
                            import json

                            event = json.loads(data)
                            event_type = event.get("type", "")

                            if event_type == "content_block_delta":
                                delta = event.get("delta", {})
                                text = delta.get("text", "")
                                if text:
                                    yield text

                            elif event_type == "message_stop":
                                break

                            elif event_type == "error":
                                error_msg = event.get("error", {}).get("message", "Unknown error")
                                logger.error("llm_stream_error", error=error_msg)
                                yield f"\n\n[Lỗi: {error_msg}]"
                                return

                        except Exception:
                            continue

        except httpx.TimeoutException:
            logger.error("llm_timeout")
            yield "\n\n[Phản hồi bị gián đoạn do timeout. Vui lòng thử lại.]"
        except Exception as e:
            logger.error("llm_stream_exception", error=str(e))
            yield "\n\n[Lỗi kết nối đến AI. Vui lòng thử lại.]"

    async def generate(
        self,
        system: str,
        user_message: str,
        model: str = "claude-haiku-4-5-20251001",
        max_tokens: int = 500,
    ) -> str:
        """
        Non-streaming generation (for Haiku classify, brief generation).

        Returns the full text response.
        """
        if not self.api_key:
            return ""

        headers = {
            "x-api-key": self.api_key,
            "anthropic-version": ANTHROPIC_VERSION,
            "content-type": "application/json",
        }

        payload = {
            "model": model,
            "max_tokens": max_tokens,
            "system": system,
            "messages": [{"role": "user", "content": user_message}],
        }

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    ANTHROPIC_API_URL, json=payload, headers=headers
                )
                response.raise_for_status()
                data = response.json()

                # Extract text from content blocks
                content = data.get("content", [])
                text_parts = [
                    block.get("text", "")
                    for block in content
                    if block.get("type") == "text"
                ]
                return "".join(text_parts)

        except Exception as e:
            logger.error("llm_generate_error", model=model, error=str(e))
            return ""
