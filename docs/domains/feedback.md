---
title: "Feedback domain"
usage: "Defines evaluation, scoring, and ranking feedback"
sources:
  - https://docs.wandb.ai/weave/guides/core-types/evaluations
---

# Feedback Domain

See `AGENTS.md` ([WV1a-d], [MO1d]).

## Feedback Flow

```
┌──────────────────────────────────────────────────────────────────────┐
│                        Feedback Pipeline                             │
│                                                                      │
│  ┌─────────────┐    ┌─────────────┐    ┌───────────────────────────┐ │
│  │  Response   │───▶│  Evaluator  │───▶│ Evaluation                │ │
│  │ (AIMessage) │    │  (Scorer)   │    │ (agentloop-state.jsonc    │ │
│  │             │    │             │    │  → evaluations[])         │ │
│  └─────────────┘    └─────────────┘    └─────────────┬─────────────┘ │
│   agentloop-                                         │               │
│   messages.jsonc                                     ▼               │
│                                        ┌───────────────────────────┐ │
│                                        │ RankingEntry              │ │
│                                        │ (agentloop-memory.jsonc   │ │
│                                        │  → ranking_entry)         │ │
│                                        └─────────────┬─────────────┘ │
│                                                      │               │
│               ┌──────────────────────────────────────┴──┐            │
│               ▼                                         ▼            │
│      ┌─────────────────────┐              ┌───────────────────────┐  │
│      │ weave-evaluation    │              │   Decider Input       │  │
│      │ .jsonc (persistence)│              │   (next action)       │  │
│      └─────────────────────┘              └───────────────────────┘  │
└──────────────────────────────────────────────────────────────────────┘
```

## Purpose

Feedback captures evaluation outcomes, rankings, and rationale used to
improve future prompt selection and decision routing.

## Core Concepts

- **Evaluation** (`agentloop-state.jsonc` → `evaluations[]`): Score + reasoning for a response.
- **RankingEntry** (`agentloop-memory.jsonc` → `ranking_entry`): Ordered comparison between responses.
- **FeedbackEntry** (`agentloop-memory.jsonc` → `feedback_entry`): User/evaluator feedback on a run.

## Weave Alignment

Evaluations are stored in-state during the loop, then persisted via
`weave-evaluation.jsonc` for cross-run comparison and quality tracking.
