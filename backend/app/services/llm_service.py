"""
Unified LLM Service
Automatically uses OpenAI or Gemini based on available API keys
"""
from __future__ import annotations

import logging
from typing import Any, AsyncGenerator

from app.core.config import settings

logger = logging.getLogger(__name__)


class UnifiedLLMService:
    """
    Unified interface for LLM operations.
    Automatically selects OpenAI or Gemini based on configuration.
    """

    def __init__(self):
        self.provider = self._detect_provider()
        logger.info(f"LLM Provider: {self.provider}")
        
        if self.provider == "openai":
            from openai import AsyncOpenAI
            self.client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
            self.chat_model = settings.OPENAI_CHAT_MODEL
            self.embedding_model = settings.OPENAI_EMBEDDING_MODEL
        elif self.provider == "gemini":
            from app.services.gemini_service import get_gemini_service
            self.client = get_gemini_service()
            self.chat_model = "gemini-1.5-flash"
            self.embedding_model = "embedding-001"
        else:
            raise RuntimeError("No LLM provider configured (need OPENAI_API_KEY or GOOGLE_API_KEY)")

    def _detect_provider(self) -> str:
        """Detect which LLM provider to use."""
        if settings.OPENAI_API_KEY and settings.OPENAI_API_KEY != "YOUR_OPENAI_API_KEY_HERE":
            return "openai"
        elif settings.GOOGLE_API_KEY and settings.GOOGLE_API_KEY != "YOUR_GOOGLE_API_KEY_HERE":
            return "gemini"
        else:
            # Default to Gemini if both are placeholders
            return "gemini"

    async def chat_completion(
        self, messages: list[dict[str, str]], temperature: float = 0.2
    ) -> dict[str, Any]:
        """
        Generate chat completion.
        
        Args:
            messages: List of message dicts with 'role' and 'content'
            temperature: Sampling temperature
            
        Returns:
            Response dict with 'choices' and 'usage'
        """
        if self.provider == "openai":
            response = await self.client.chat.completions.create(
                model=self.chat_model,
                messages=messages,
                temperature=temperature,
            )
            return {
                "choices": [
                    {
                        "message": {
                            "role": "assistant",
                            "content": response.choices[0].message.content or "",
                        },
                        "finish_reason": response.choices[0].finish_reason,
                    }
                ],
                "usage": {
                    "total_tokens": response.usage.total_tokens if response.usage else 0,
                },
            }
        else:  # gemini
            return await self.client.chat_completion(messages, temperature)

    async def chat_completion_stream(
        self, messages: list[dict[str, str]], temperature: float = 0.2
    ) -> AsyncGenerator[str, None]:
        """
        Stream chat completion tokens.
        
        Args:
            messages: List of message dicts
            temperature: Sampling temperature
            
        Yields:
            Text chunks
        """
        if self.provider == "openai":
            async with self.client.chat.completions.stream(
                model=self.chat_model,
                messages=messages,
                temperature=temperature,
            ) as stream:
                async for event in stream:
                    delta = event.choices[0].delta.content if event.choices else None
                    if delta:
                        yield delta
        else:  # gemini
            async for chunk in self.client.chat_completion_stream(messages, temperature):
                yield chunk

    async def generate_embeddings(self, texts: list[str]) -> list[list[float]]:
        """
        Generate embeddings for texts.
        
        Args:
            texts: List of text strings
            
        Returns:
            List of embedding vectors
        """
        if self.provider == "openai":
            response = await self.client.embeddings.create(
                model=self.embedding_model,
                input=texts,
            )
            return [item.embedding for item in response.data]
        else:  # gemini
            return await self.client.generate_embeddings(texts)

    async def transcribe_audio(self, audio_path: str) -> str:
        """
        Transcribe audio file.
        
        Args:
            audio_path: Path to audio file
            
        Returns:
            Transcribed text
        """
        if self.provider == "openai":
            with open(audio_path, "rb") as audio_file:
                response = await self.client.audio.transcriptions.create(
                    model="whisper-1",
                    file=audio_file,
                )
            return response.text
        else:  # gemini
            # Gemini doesn't support audio transcription
            # Fall back to local Whisper or raise error
            logger.warning("Gemini doesn't support audio transcription")
            raise NotImplementedError(
                "Audio transcription requires OpenAI Whisper API. "
                "Please set OPENAI_API_KEY or use local Whisper model."
            )

    def get_embedding_dimension(self) -> int:
        """Get embedding vector dimension for current provider."""
        if self.provider == "openai":
            return 1536  # text-embedding-3-small
        else:  # gemini
            return 768  # embedding-001


# Singleton instance
_llm_service: UnifiedLLMService | None = None


def get_llm_service() -> UnifiedLLMService:
    """Get or create unified LLM service singleton."""
    global _llm_service
    if _llm_service is None:
        _llm_service = UnifiedLLMService()
    return _llm_service
