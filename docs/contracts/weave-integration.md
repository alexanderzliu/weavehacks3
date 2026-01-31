---
title: "Weave integration contract"
usage: "How to use Weave for observability, memory, and evaluations"
sources:
  - https://docs.wandb.ai/weave/quickstart
  - https://docs.wandb.ai/weave/guides/tracking/objects
  - https://docs.wandb.ai/weave/guides/tracking/ops
  - https://docs.wandb.ai/weave/guides/core-types/evaluations
  - https://docs.wandb.ai/weave/guides/core-types/datasets
  - https://docs.wandb.ai/weave/guides/core-types/models
---

# Weave Integration Contract

See `AGENTS.md` ([WV1a-d]).

## Core Weave Objects

Weave provides these core object types we use:

| Object Type | Purpose | Our Usage |
|-------------|---------|-----------|
| `weave.Object` | Versioned persistent storage | Memory, patterns, rankings |
| `Dataset` | Collection of examples | Evaluation datasets |
| `Model` | Versioned application code | Agent configurations |
| `Evaluation` | Systematic assessment | Response quality |
| `Call` | Traced operation | All agent operations |

**Source:** [Weave Objects](https://docs.wandb.ai/weave/guides/tracking/objects)

## Initialization

```python
import weave

# Initialize once at application startup
# Ref: https://docs.wandb.ai/weave/quickstart
weave.init("agent-loop")
```

## Tracing with @weave.op()

Every function that calls an LLM, makes a decision, or evaluates results
MUST be decorated with `@weave.op()`.

**Source:** [Weave Ops](https://docs.wandb.ai/weave/guides/tracking/ops)

```python
@weave.op()
async def agent_node(state: AgentState) -> dict:
    """Traced automatically - inputs, outputs, timing, errors."""
    # Weave captures: inputs, outputs, latency, exceptions
    ...
```

### Op Display Names

Use the `name` parameter to set a static operation name in traces:

```python
@weave.op(name="execute_tool")
def execute_tool(tool_name: str, args: dict) -> ToolResult:
    ...
```

For dynamic display names based on inputs, use `call_display_name` with a callable:

```python
# call_display_name receives the inputs dict and returns a string
@weave.op(call_display_name=lambda inputs: f"Agent Loop: {inputs['task'][:50]}")
async def arun(self, task: str) -> AgentLoopResult:
    ...
```

**Important:** `call_display_name` must be a callable (function/lambda), not a string.
String interpolation syntax like `"{task[:50]}"` will NOT work because decorators
are evaluated at definition time, not call time.

**Source:** https://docs.wandb.ai/weave/guides/tracking/ops

## Persistent Objects with weave.Object

Weave objects are JSON-serializable and versioned automatically.

**Source:** [Track and version objects](https://docs.wandb.ai/weave/guides/tracking/objects)

### Publishing Objects

```python
import weave

# Save any JSON-serializable object
# Ref: https://docs.wandb.ai/weave/guides/tracking/objects#publishing-an-object
weave.publish({"patterns": [...], "scores": [...]}, "learned-patterns")
```

### Retrieving Objects

```python
# Get object back by name (uses :latest by default)
# Ref: https://docs.wandb.ai/weave/guides/tracking/objects#getting-an-object-back
patterns = weave.ref("learned-patterns").get()

# Get specific version
patterns_v1 = weave.ref("learned-patterns:v1").get()
```

### Ref URI Format

Full ref format: `weave://<<entity>>/<<project>>/object/<<name>>:<<version>>`

**Source:** [Ref styles](https://docs.wandb.ai/weave/guides/tracking/objects#ref-styles)

## Datasets

Datasets organize examples for evaluation.

**Source:** [Collect and track datasets](https://docs.wandb.ai/weave/guides/core-types/datasets)

```python
from weave import Dataset

# Create dataset
# Ref: https://docs.wandb.ai/weave/guides/core-types/datasets#dataset-quickstart
dataset = Dataset(
    name="evaluation-examples",
    rows=[
        {"task": "Summarize...", "expected": "..."},
        {"task": "Analyze...", "expected": "..."},
    ]
)

# Publish
weave.publish(dataset)

# Retrieve
dataset_ref = weave.ref("evaluation-examples").get()
```

## Evaluations

Evaluations systematically measure agent behavior.

**Source:** [Evaluations overview](https://docs.wandb.ai/weave/guides/core-types/evaluations)

### Evaluation Structure

```python
from weave import Evaluation

# Ref: https://docs.wandb.ai/weave/guides/core-types/evaluations#1-create-an-evaluation-object
evaluation = Evaluation(
    dataset=examples,  # List or Dataset
    scorers=[accuracy_scorer, quality_scorer],
    evaluation_name="agent-quality"
)

# Run evaluation
# Ref: https://docs.wandb.ai/weave/guides/core-types/evaluations#5-run-the-evaluation
await evaluation.evaluate(model_or_function)
```

### Scoring Functions

```python
@weave.op()
def match_score(expected: str, output: dict) -> dict:
    """Scorer function - must have 'output' parameter.
    
    Ref: https://docs.wandb.ai/weave/guides/core-types/evaluations#3-define-scoring-functions
    """
    return {"match": expected == output["response"]}
```

## Models (Versioned Applications)

Track application versions with structured models.

**Source:** [Track application versions](https://docs.wandb.ai/weave/guides/core-types/models)

```python
from weave import Model

class AgentModel(Model):
    """Versioned agent configuration.
    
    Ref: https://docs.wandb.ai/weave/guides/core-types/models
    """
    system_prompt: str
    temperature: float
    
    @weave.op()
    def predict(self, task: str) -> dict:
        # Agent logic
        return {"response": "..."}
```

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `WANDB_API_KEY` | Yes | Weights & Biases API key |
| `WEAVE_PROJECT` | No | Override project name |

## JSON Schema References

See `docs/api-contracts/json-examples/` for canonical JSON structures:
- `weave-object.jsonc` - Generic Weave object
- `weave-dataset.jsonc` - Dataset structure
- `weave-evaluation.jsonc` - Evaluation structure
- `weave-model.jsonc` - Model structure
- `weave-call.jsonc` - Call/trace structure (subset)
