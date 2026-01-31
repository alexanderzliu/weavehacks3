---
title: "Feedback domain"
usage: "Defines evaluation, scoring, and ranking feedback"
sources:
  - https://docs.wandb.ai/weave/guides/core-types/evaluations
---

# Feedback Domain

See `AGENTS.md` ([WV1a-d], [MO1d]).

## Purpose

Feedback captures evaluation outcomes, rankings, and rationale used to
improve future prompt selection and decision routing.

**Source:** https://docs.wandb.ai/weave/guides/core-types/evaluations

## Core Concepts

- **EvaluationResult**: Score set + reasoning for a response.
- **RankingEntry**: Ordered comparison between candidate responses.
- **FeedbackRequest**: Optional user feedback attached to a run.

## Weave Alignment

Evaluations and scorers are implemented as Weave ops and stored via Weave
evaluation workflows so they can be queried and compared across runs.

**Source:** https://docs.wandb.ai/weave/guides/core-types/evaluations
