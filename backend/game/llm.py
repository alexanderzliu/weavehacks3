"""Unified LLM client with retry logic and structured output."""

import asyncio
import json
from typing import TypeVar

import anthropic
import openai
from google import genai
from google.genai import types as genai_types
from pydantic import BaseModel

from config import get_settings
from models.schemas import ModelProvider

settings = get_settings()

T = TypeVar("T", bound=BaseModel)


class LLMError(Exception):
    """Base exception for LLM errors."""

    pass


class LLMConfigError(LLMError):
    """Missing or invalid API key configuration."""

    pass


class LLMTimeoutError(LLMError):
    """Timeout during LLM call."""

    pass


class LLMParseError(LLMError):
    """Failed to parse LLM response."""

    pass


def get_available_providers() -> list[ModelProvider]:
    """Return list of providers with configured API keys."""
    available = []
    if settings.ANTHROPIC_API_KEY:
        available.append(ModelProvider.ANTHROPIC)
    if settings.OPENAI_API_KEY:
        available.append(ModelProvider.OPENAI)
    if settings.GOOGLE_API_KEY:
        available.append(ModelProvider.GOOGLE)
    if settings.OPENAI_COMPATIBLE_BASE_URL and settings.OPENAI_COMPATIBLE_API_KEY:
        available.append(ModelProvider.OPENAI_COMPATIBLE)
    if settings.OPENROUTER_API_KEY:
        available.append(ModelProvider.OPENROUTER)
    if settings.WANDB_API_KEY:
        available.append(ModelProvider.WANDB)
    return available


# Map user-friendly IDs to full W&B Inference model names
WANDB_MODEL_MAP = {
    "llama-3.1-8b": "meta-llama/Llama-3.1-8B-Instruct",
    "qwen3-235b": "Qwen/Qwen3-235B-A22B-Instruct-2507",
    "deepseek-v3": "deepseek-ai/DeepSeek-V3-0324",
    "llama-3.3-70b": "meta-llama/Llama-3.3-70B-Instruct",
    "gpt-oss-20b": "openai/GPT-OSS-20B",
}


class LLMClient:
    """Unified client for multiple LLM providers."""

    def __init__(self):
        self._anthropic: anthropic.AsyncAnthropic | None = None
        self._openai: openai.AsyncOpenAI | None = None
        self._openai_compatible: openai.AsyncOpenAI | None = None
        self._openrouter: openai.AsyncOpenAI | None = None
        self._google: genai.Client | None = None
        self._wandb: openai.AsyncOpenAI | None = None

    def _get_anthropic(self) -> anthropic.AsyncAnthropic:
        if self._anthropic is None:
            self._anthropic = anthropic.AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY)
        return self._anthropic

    def _get_openai(self) -> openai.AsyncOpenAI:
        if self._openai is None:
            self._openai = openai.AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
        return self._openai

    def _get_openai_compatible(self) -> openai.AsyncOpenAI:
        if self._openai_compatible is None:
            self._openai_compatible = openai.AsyncOpenAI(
                api_key=settings.OPENAI_COMPATIBLE_API_KEY,
                base_url=settings.OPENAI_COMPATIBLE_BASE_URL,
            )
        return self._openai_compatible

    def _get_openrouter(self) -> openai.AsyncOpenAI:
        if self._openrouter is None:
            self._openrouter = openai.AsyncOpenAI(
                api_key=settings.OPENROUTER_API_KEY,
                base_url="https://openrouter.ai/api/v1",
            )
        return self._openrouter

    def _get_google(self) -> genai.Client:
        if self._google is None:
            self._google = genai.Client(api_key=settings.GOOGLE_API_KEY)
        return self._google

    def _get_wandb(self) -> openai.AsyncOpenAI:
        if self._wandb is None:
            self._wandb = openai.AsyncOpenAI(
                base_url="https://api.inference.wandb.ai/v1",
                api_key=settings.WANDB_API_KEY,
            )
        return self._wandb

    async def complete(
        self,
        provider: ModelProvider,
        model_name: str,
        system_prompt: str,
        user_prompt: str,
        timeout: int | None = None,
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
            elif provider == ModelProvider.OPENAI_COMPATIBLE:
                return await asyncio.wait_for(
                    self._openai_chat_complete(
                        self._get_openai_compatible(), model_name, system_prompt, user_prompt
                    ),
                    timeout=timeout,
                )
            elif provider == ModelProvider.OPENROUTER:
                return await asyncio.wait_for(
                    self._openai_chat_complete(
                        self._get_openrouter(), model_name, system_prompt, user_prompt
                    ),
                    timeout=timeout,
                )
            elif provider == ModelProvider.WANDB:
                return await asyncio.wait_for(
                    self._wandb_complete(model_name, system_prompt, user_prompt),
                    timeout=timeout,
                )
            else:
                raise LLMError(f"Unknown provider: {provider}")
        except TimeoutError as e:
            raise LLMTimeoutError(f"LLM call timed out after {timeout}s") from e

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

    async def _openai_chat_complete(
        self,
        client: openai.AsyncOpenAI,
        model_name: str,
        system_prompt: str,
        user_prompt: str,
    ) -> str:
        """Shared completion logic for OpenAI and OpenAI-compatible endpoints."""
        response = await client.chat.completions.create(
            model=model_name,
            max_completion_tokens=2048,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        )
        content = response.choices[0].message.content
        if content is None:
            raise LLMError("OpenAI-style endpoint returned empty response")
        return content

    async def _openai_complete(
        self,
        model_name: str,
        system_prompt: str,
        user_prompt: str,
    ) -> str:
        return await self._openai_chat_complete(
            self._get_openai(), model_name, system_prompt, user_prompt
        )

    async def _google_complete(
        self,
        model_name: str,
        system_prompt: str,
        user_prompt: str,
    ) -> str:
        client = self._get_google()
        response = await client.aio.models.generate_content(
            model=model_name,
            contents=user_prompt,
            config=genai_types.GenerateContentConfig(
                system_instruction=system_prompt,
                max_output_tokens=2048,
            ),
        )
        if response.text is None:
            raise LLMError("Google Gemini returned empty response")
        return response.text

    async def _wandb_complete(
        self,
        model_name: str,
        system_prompt: str,
        user_prompt: str,
    ) -> str:
        # Map short ID to full model name
        full_model_name = WANDB_MODEL_MAP.get(model_name, model_name)
        client = self._get_wandb()
        response = await client.chat.completions.create(
            model=full_model_name,
            max_completion_tokens=2048,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        )
        return response.choices[0].message.content

    async def complete_json(
        self,
        provider: ModelProvider,
        model_name: str,
        system_prompt: str,
        user_prompt: str,
        response_model: type[T],
        timeout: int | None = None,
        max_retries: int | None = None,
    ) -> T:
        """Get a structured JSON response, with retry logic."""
        max_retries = max_retries if max_retries is not None else settings.LLM_MAX_RETRIES
        last_error: Exception | None = None

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

    def _parse_json_response(self, text: str, response_model: type[T]) -> T:
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
            parsed_json = json.loads(text)
            return response_model.model_validate(parsed_json)
        except json.JSONDecodeError as e:
            raise LLMParseError(f"Invalid JSON: {e}") from e
        except Exception as e:
            raise LLMParseError(f"Validation error: {e}") from e


# Global LLM client instance
llm_client = LLMClient()
