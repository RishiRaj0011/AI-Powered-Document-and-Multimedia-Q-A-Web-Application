"""
Google Gemini API Service
Provides OpenAI-compatible interface for Gemini models
"""
from __future__ import annotations

import logging
from typing import Any, AsyncGenerator

import google.generativeai as genai
from google.generativeai.types import GenerateContentResponse

from app.core.config import settings

logger = logging.getLogger(__name__)

# Configure Gemini
if settings.GOOGLE_API_KEY:
    genai.configure(api_key=settings.GOOGLE_API_KEY)

# Model configuration
GEMINI_MODEL = "gemini-1.5-flash"  # Free tier: 15 RPM, 1M TPM
GEMINI_EMBEDDING_MODEL = "models/embedding-001"  # 768-dim embeddings


class GeminiService:
    """Wrapper for Google Gemini API with OpenAI-compatible interface."""

    def __init__(self):
        self.model = genai.GenerativeModel(GEMINI_MODEL)
        self.chat_model = genai.GenerativeModel(
            GEMINI_MODEL,
            generation_config={
                "temperature": 0.2,
                "top_p": 0.8,
                "top_k": 40,
                "max_output_tokens": 2048,
            },
        )

    async def chat_completion(
        self, messages: list[dict[str, str]], temperature: float = 0.2
    ) -> dict[str, Any]:
        """
        OpenAI-compatible chat completion.
        
        Args:
            messages: List of message dicts with 'role' and 'content'
            temperature: Sampling temperature
            
        Returns:
            Dict with 'choices' containing response
        """
        try:
            # Convert OpenAI format to Gemini format
            prompt = self._convert_messages_to_prompt(messages)
            
            # Generate response
            response = await self.model.generate_content_async(
                prompt,
                generation_config={"temperature": temperature},
            )
            
            # Convert to OpenAI format
            return {
                "choices": [
                    {
                        "message": {
                            "role": "assistant",
                            "content": response.text,
                        },
                        "finish_reason": "stop",
                    }
                ],
                "usage": {
                    "total_tokens": self._estimate_tokens(prompt, response.text),
                },
            }
        except Exception as e:
            logger.error(f"Gemini chat completion error: {e}")
            raise

    async def chat_completion_stream(
        self, messages: list[dict[str, str]], temperature: float = 0.2
    ) -> AsyncGenerator[str, None]:
        """
        Stream chat completion tokens.
        
        Args:
            messages: List of message dicts
            temperature: Sampling temperature
            
        Yields:
            Text chunks as they're generated
        """
        try:
            prompt = self._convert_messages_to_prompt(messages)
            
            response = await self.model.generate_content_async(
                prompt,
                generation_config={"temperature": temperature},
                stream=True,
            )
            
            async for chunk in response:
                if chunk.text:
                    yield chunk.text
                    
        except Exception as e:
            logger.error(f"Gemini streaming error: {e}")
            raise

    async def generate_embeddings(self, texts: list[str]) -> list[list[float]]:
        """
        Generate embeddings for texts.
        
        Args:
            texts: List of text strings
            
        Returns:
            List of embedding vectors (768-dim)
        """
        try:
            embeddings = []
            for text in texts:
                result = genai.embed_content(
                    model=GEMINI_EMBEDDING_MODEL,
                    content=text,
                    task_type="retrieval_document",
                )
                embeddings.append(result["embedding"])
            return embeddings
        except Exception as e:
            logger.error(f"Gemini embedding error: {e}")
            raise

    async def transcribe_audio(self, audio_path: str) -> dict[str, Any]:
        """
        Transcribe audio file using Gemini.
        
        Note: Gemini doesn't have direct audio transcription.
        This is a placeholder - use Whisper API or local Whisper model.
        
        Args:
            audio_path: Path to audio file
            
        Returns:
            Dict with 'text' key
        """
        logger.warning("Gemini doesn't support audio transcription - use Whisper")
        raise NotImplementedError(
            "Audio transcription requires OpenAI Whisper or local Whisper model"
        )

    def _convert_messages_to_prompt(self, messages: list[dict[str, str]]) -> str:
        """Convert OpenAI message format to Gemini prompt."""
        prompt_parts = []
        
        for msg in messages:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            
            if role == "system":
                prompt_parts.append(f"Instructions: {content}\n")
            elif role == "user":
                prompt_parts.append(f"User: {content}\n")
            elif role == "assistant":
                prompt_parts.append(f"Assistant: {content}\n")
        
        return "\n".join(prompt_parts)

    def _estimate_tokens(self, prompt: str, response: str) -> int:
        """Rough token estimation (4 chars per token)."""
        return (len(prompt) + len(response)) // 4


# Singleton instance
_gemini_service: GeminiService | None = None


def get_gemini_service() -> GeminiService:
    """Get or create Gemini service singleton."""
    global _gemini_service
    if _gemini_service is None:
        _gemini_service = GeminiService()
    return _gemini_service
