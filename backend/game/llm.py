"""Unified LLM client with retry logic and structured output."""
import asyncio
import json
from typing import Any, Optional, TypeVar, Type
from pydantic import BaseModel

import anthropic
import openai
import google.generativeai as genai

from config import get_settings
from models.schemas import ModelProvider

settings = get_settings()

T = TypeVar("T", bound=BaseModel)


class LLMError(Exception):
    """Base exception for LLM errors."""
    pass


class LLMTimeoutError(LLMError):
    """Timeout during LLM call."""
    pass


class LLMParseError(LLMError):
    """Failed to parse LLM response."""
    pass


class LLMClient:
    """Unified client for multiple LLM providers."""

    def __init__(self):
        self._anthropic: Optional[anthropic.AsyncAnthropic] = None
        self._openai: Optional[openai.AsyncOpenAI] = None
        self._google_configured = False

    def _get_anthropic(self) -> anthropic.AsyncAnthropic:
        if self._anthropic is None:
            self._anthropic = anthropic.AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY)
        return self._anthropic

    def _get_openai(self) -> openai.AsyncOpenAI:
        if self._openai is None:
            self._openai = openai.AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
        return self._openai

    def _ensure_google(self) -> None:
        if not self._google_configured:
            genai.configure(api_key=settings.GOOGLE_API_KEY)
            self._google_configured = True

    async def complete(
        self,
        provider: ModelProvider,
        model_name: str,
        system_prompt: str,
        user_prompt: str,
        timeout: Optional[int] = None,
    ) -> str:
        """Get a text completion from the specified provider."""
        timeout = timeout or settings.DEFAULT_TIMEOUT_SECONDS

        try:
            if provider == ModelProvider.ANTHROPIC:
                return await asyncio.wait_for(
                    self._anthropic_complete(model_name, system_prompt, user_prompt),
                    timeout=timeout,
                )
            elif provider == ModelProvider.OPENAI:
                return await asyncio.wait_for(
                    self._openai_complete(model_name, system_prompt, user_prompt),
                    timeout=timeout,
                )
            elif provider == ModelProvider.GOOGLE:
                return await asyncio.wait_for(
                    self._google_complete(model_name, system_prompt, user_prompt),
                    timeout=timeout,
                )
            else:
                raise LLMError(f"Unknown provider: {provider}")
        except asyncio.TimeoutError:
            raise LLMTimeoutError(f"LLM call timed out after {timeout}s")

    async def _anthropic_complete(
        self,
        model_name: str,
        system_prompt: str,
        user_prompt: str,
    ) -> str:
        client = self._get_anthropic()
        response = await client.messages.create(
            model=model_name,
            max_tokens=2048,
            system=system_prompt,
            messages=[{"role": "user", "content": user_prompt}],
        )
        return response.content[0].text

    async def _openai_complete(
        self,
        model_name: str,
        system_prompt: str,
        user_prompt: str,
    ) -> str:
        client = self._get_openai()
        response = await client.chat.completions.create(
            model=model_name,
            max_completion_tokens=2048,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        )
        return response.choices[0].message.content

    async def _google_complete(
        self,
        model_name: str,
        system_prompt: str,
        user_prompt: str,
    ) -> str:
        self._ensure_google()
        # Google's generativeai library is synchronous, run in executor
        loop = asyncio.get_event_loop()
        model = genai.GenerativeModel(
            model_name,
            system_instruction=system_prompt,
        )

        def sync_generate():
            response = model.generate_content(user_prompt)
            return response.text

        return await loop.run_in_executor(None, sync_generate)

    async def complete_json(
        self,
        provider: ModelProvider,
        model_name: str,
        system_prompt: str,
        user_prompt: str,
        response_model: Type[T],
        timeout: Optional[int] = None,
        max_retries: Optional[int] = None,
    ) -> T:
        """Get a structured JSON response, with retry logic."""
        max_retries = max_retries if max_retries is not None else settings.LLM_MAX_RETRIES
        last_error: Optional[Exception] = None

        # Add JSON instruction to system prompt
        json_system_prompt = f"""{system_prompt}

IMPORTANT: You must respond with valid JSON only. No markdown code blocks, no explanations outside JSON.
The response must conform to this schema:
{response_model.model_json_schema()}"""

        for attempt in range(max_retries + 1):
            try:
                response_text = await self.complete(
                    provider=provider,
                    model_name=model_name,
                    system_prompt=json_system_prompt,
                    user_prompt=user_prompt,
                    timeout=timeout,
                )

                # Try to parse JSON
                parsed = self._parse_json_response(response_text, response_model)
                return parsed

            except LLMTimeoutError:
                last_error = LLMTimeoutError(f"Timeout after {attempt + 1} attempts")
            except LLMParseError as e:
                last_error = e
            except Exception as e:
                last_error = LLMError(f"LLM error: {e}")

            if attempt < max_retries:
                # Brief delay before retry
                await asyncio.sleep(0.5)

        raise last_error or LLMError("Unknown error")

    def _parse_json_response(self, text: str, response_model: Type[T]) -> T:
        """Parse a JSON response, handling common formatting issues."""
        # Strip markdown code blocks if present
        text = text.strip()
        if text.startswith("```json"):
            text = text[7:]
        elif text.startswith("```"):
            text = text[3:]
        if text.endswith("```"):
            text = text[:-3]
        text = text.strip()

        try:
            data = json.loads(text)
            return response_model.model_validate(data)
        except json.JSONDecodeError as e:
            raise LLMParseError(f"Invalid JSON: {e}")
        except Exception as e:
            raise LLMParseError(f"Validation error: {e}")


# Global LLM client instance
llm_client = LLMClient()
