---
title: "LLM providers contract"
usage: "How to integrate LLM providers using LangChain primitives"
sources:
  - https://python.langchain.com/docs/concepts/#chat-models
  - https://python.langchain.com/docs/integrations/chat/
---

# LLM Providers Contract

See `AGENTS.md` ([LM1c], [LM1d]).

## Core Principles

1.  **Standard Interface**: Use `langchain_core.language_models.BaseChatModel`.
2.  **No Custom Adapters**: Use LangChain's built-in integrations (OpenAI, Anthropic, etc.).
3.  **Factory Pattern**: Centralize instantiation in `adapters/llm/factory.py`.

## Implementation Pattern

We use `BaseChatModel` as our primary domain interface. This allows us to plug in any supported provider without custom adapter classes.

```python
# adapters/llm/factory.py
from langchain_core.language_models import BaseChatModel
from langchain_openai import ChatOpenAI

def create_llm_provider(
    provider: str,
    model: str | None = None,
    api_key: str | None = None,
    base_url: str | None = None,
) -> BaseChatModel:
    if provider == "openai":
        return ChatOpenAI(
            api_key=api_key or os.getenv("OPENAI_API_KEY"),
            model=model or "gpt-4o",
        )
    # ... handle other providers
```

## Domain Models

We use `langchain_core` messages as our primitives.

```python
from langchain_core.messages import (
    HumanMessage, 
    AIMessage, 
    SystemMessage, 
    ToolMessage
)
```

## Rules

-   **[LM1c]** Use `BaseChatModel` from `langchain_core` as the domain interface.
-   **[LM1d]** Factory in `adapters/llm/` instantiates concrete LangChain chat models.
