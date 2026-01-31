---
title: "LangGraph state contract"
usage: "How to use LangGraph for agent orchestration and persistence"
sources:
  - https://langchain-ai.github.io/langgraph/concepts/persistence/
  - https://langchain-ai.github.io/langgraph/concepts/low_level/
  - https://docs.langchain.com/oss/python/langgraph/graph-api
---

# LangGraph State Contract

See `AGENTS.md` ([LG1a-d]).

## Core LangGraph Concepts

| Concept | Purpose | Our Usage |
|---------|---------|-----------|
| `StateGraph` | Define graph structure | Main orchestrator |
| `State` | Typed state schema | Agent loop state |
| `Checkpointer` | Thread persistence | Conversation continuity |
| `Memory Store` | Cross-thread storage | Learned patterns |
| `Command` | State + routing | Navigation decisions |

**Source:** [LangGraph Persistence](https://langchain-ai.github.io/langgraph/concepts/persistence/)

## State Definition

State is defined as TypedDict or Pydantic model.

**Source:** [Graph API - State](https://docs.langchain.com/oss/python/langgraph/graph-api#state)

```python
from typing import TypedDict, Annotated
from langgraph.graph import add_messages

class LoopState(TypedDict):
    """Primary state for the agent loop.
    
    Ref: https://docs.langchain.com/oss/python/langgraph/graph-api#schema
    """
    # Messages with reducer for append behavior
    messages: Annotated[list, add_messages]
    
    # Simple fields (overwrite on update)
    task: str
    response: str | None
```

### Reducers

Reducers define how state updates are applied.

**Source:** [Graph API - Reducers](https://docs.langchain.com/oss/python/langgraph/graph-api#reducers)

```python
from operator import add

class State(TypedDict):
    # No reducer - overwrites on update
    current_value: str
    
    # With reducer - appends on update
    history: Annotated[list[str], add]
```

### MessagesState

Use built-in `MessagesState` for chat applications.

**Source:** [Graph API - MessagesState](https://docs.langchain.com/oss/python/langgraph/graph-api#messagesstate)

```python
from langgraph.graph import MessagesState

class State(MessagesState):
    """Extends MessagesState with custom fields."""
    task: str
    observations: list[dict]
```

## Checkpoints and Threads

Checkpoints save graph state at each super-step.

**Source:** [Persistence - Checkpoints](https://langchain-ai.github.io/langgraph/concepts/persistence/#checkpoints)

### Thread Configuration

```python
# Thread ID is required for persistence
# Ref: https://langchain-ai.github.io/langgraph/concepts/persistence/#threads
config = {"configurable": {"thread_id": "user-session-123"}}

result = await graph.invoke(state, config=config)
```

### StateSnapshot

Checkpoint data is represented as `StateSnapshot`:

```python
# Ref: https://langchain-ai.github.io/langgraph/concepts/persistence/#checkpoints
snapshot = graph.get_state(config)
# snapshot.values - Current state values
# snapshot.next - Tuple of next node names
# snapshot.config - Config with checkpoint_id
# snapshot.metadata - Source, writes, step
```

### Checkpointer Options

| Checkpointer | Use Case |
|--------------|----------|
| `InMemorySaver` | Development/testing |
| `SqliteSaver` | Local persistence |
| `PostgresSaver` | Production |

**Source:** [Checkpointer libraries](https://langchain-ai.github.io/langgraph/concepts/persistence/#checkpointer-libraries)

```python
from langgraph.checkpoint.memory import InMemorySaver

# Compile with checkpointer
# Ref: https://langchain-ai.github.io/langgraph/concepts/persistence/
checkpointer = InMemorySaver()
graph = builder.compile(checkpointer=checkpointer)
```

## Memory Store (Cross-Thread)

Memory Store enables sharing data across threads.

**Source:** [Persistence - Memory Store](https://langchain-ai.github.io/langgraph/concepts/persistence/#memory-store)

### Basic Usage

```python
from langgraph.store.memory import InMemoryStore

# Ref: https://langchain-ai.github.io/langgraph/concepts/persistence/#basic-usage
store = InMemoryStore()

# Namespace by user/type
namespace = ("user-123", "patterns")

# Store data
store.put(namespace, "pattern-id", {"pattern": "...", "score": 0.8})

# Retrieve data
memories = store.search(namespace)
memory = memories[-1].dict()
# Returns: {value, key, namespace, created_at, updated_at}
```

### Semantic Search

```python
from langchain.embeddings import init_embeddings

# Ref: https://langchain-ai.github.io/langgraph/concepts/persistence/#semantic-search
store = InMemoryStore(
    index={
        "embed": init_embeddings("openai:text-embedding-3-small"),
        "dims": 1536,
        "fields": ["$"]  # Fields to embed
    }
)

# Search by meaning
memories = store.search(namespace, query="effective prompts", limit=3)
```

### Using in Graph

```python
from langgraph.store.memory import InMemoryStore
from langgraph.checkpoint.memory import InMemorySaver

# Ref: https://langchain-ai.github.io/langgraph/concepts/persistence/#using-in-langgraph
checkpointer = InMemorySaver()
store = InMemoryStore()

graph = builder.compile(checkpointer=checkpointer, store=store)

# Access in nodes via store parameter
def my_node(state, config, *, store):
    user_id = config["configurable"]["user_id"]
    memories = store.search((user_id, "patterns"))
    ...
```

## Graph Construction

### Nodes

```python
from langgraph.graph import StateGraph, START, END

# Ref: https://docs.langchain.com/oss/python/langgraph/graph-api#nodes
builder = StateGraph(State)

def my_node(state: State) -> dict:
    return {"field": "updated_value"}

builder.add_node("my_node", my_node)
```

### Edges

```python
# Normal edge
# Ref: https://docs.langchain.com/oss/python/langgraph/graph-api#normal-edges
builder.add_edge("node_a", "node_b")

# Conditional edge
# Ref: https://docs.langchain.com/oss/python/langgraph/graph-api#conditional-edges
def route(state):
    if state["done"]:
        return END
    return "next_node"

builder.add_conditional_edges("node_a", route)
```

### Command (State + Routing)

```python
from langgraph.types import Command
from typing import Literal

# Ref: https://docs.langchain.com/oss/python/langgraph/graph-api#command
def my_node(state) -> Command[Literal["next_node"]]:
    return Command(
        update={"field": "value"},  # State update
        goto="next_node"            # Routing
    )
```

## JSON Schema References

See `docs/api-contracts/json-examples/` for canonical JSON structures:
- `langgraph-state.jsonc` - State structure
- `langgraph-checkpoint.jsonc` - Checkpoint/StateSnapshot
- `langgraph-memory-item.jsonc` - Memory store item
