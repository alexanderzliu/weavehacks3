---
description: "agent-loop: Self-improving agentic abstraction with Weave observability and LangGraph orchestration"
alwaysApply: true
---

Core standards:

- Use Weave objects/ops and LangGraph state/graphs as primitives; do not reinvent
- Clean Code requirements are strictly enforced; we follow DDD
- Before editing or creating any file, read `docs/contracts/project-code-requirements.md`
- Canonical reference: `docs/contracts/project-code-requirements.md`

IMPORTANT: Use `ty` (astral-sh/ty) for Python type checking. Run `uv run ty check` before commits.

# agent-loop Agent Rules

AGENTS.md (includes symlinks like CLAUDE.md) is the index and enforcement surface. **All hashed rules must be stated succinctly in this file**. Supporting documentation lives under `docs/` by narrow topic (each file <= 350 LOC) and explains **how** and **why** when needed. `docs/agents/` must not exist.

## Document Organization [ORG]

- Purpose: keep every critical rule referenceable by short hashes.
- Structure: rule summary below; rules are expressed as succinct hashed statements.
- Usage: cite hashes when giving guidance or checking compliance; add new hashes in logical order without renumbering older ones; put deep rationale in `docs/` by topic.
- [ORG1] One Hash, One Rule: each `[XX#x]` bullet is a single, succinct rule statement. Put HOW/WHY in `docs/` (<= 350 LOC each) and reference it from the rule.

## [LC1] Line Count Ceiling (Repo-Wide)

- Contract: `docs/contracts/project-code-requirements.md`
- [LC1a] All written, non-generated source files in this repository MUST be <= 350 lines (`wc -l`), including `AGENTS.md`
- [LC1b] SRP Enforcer: This 350-line "stick" forces modularity (DDD/SRP); > 350 lines = too many responsibilities (see [MO1d])
- [LC1c] Zero Tolerance: No edits allowed to files > 350 LOC (even legacy); you MUST split/retrofit before applying your change
- [LC1d] Exempt files: generated content (`**/generated/**`), lockfiles, JSON data dumps

## [DOC1] Documentation Architecture (Mandatory)

- [DOC1a] Canonical rules: `AGENTS.md` is the ONLY canonical source for agent rules; rules live here as succinct hashed bullets (see [ORG1]).
- [DOC1b] Docs purpose: `docs/` files explain HOW and WHY to follow rules; docs MUST NOT restate/redefine rules; reference rule IDs instead.
- [DOC1c] Docs scope: each `docs/*.md` file covers one narrow topic and MUST be <= 350 lines (see [LC1a]).
- [DOC1d] No doc barrels: do not create docs whose primary purpose is listing other docs. Every doc must be substantive.
- [DOC1e] Prerequisite reading: when a workflow requires a doc to be read first, the rule MUST name the exact doc path.

## [DOC2] Docs Are Evergreen (Mandatory)

- [DOC2a] Evergreen only: no PR references, dates, "this week", or editorial tone in evergreen docs
- [DOC2b] No task logs: investigations/checklists belong in issues/PRs; only keep content in `docs/` if converted into a timeless contract/pattern

## Rule Summary [SUM]

### [ZA1] Epistemic Humility

- [ZA1a] Your training data for APIs/versions is FALSE until verified; assume you are blind
- [ZA1b] Mandatory Scout Phase: Before coding, verify existence/signatures of APIs and libraries via docs/tools
- [ZA1c] Uncommitted changes are presumed intentional; never revert unless explicitly asked

### [PM1] Package Management

- [PM1a] Use `uv` for all package operations; NO `pip` or `requirements.txt`
- [PM1b] Add packages: `uv add <package>` (updates `pyproject.toml` automatically)
- [PM1c] Source of truth: `pyproject.toml`

### [GT1] Git Standards

- [GT1a] Git writes require explicit permission
- [GT1b] Read-only git is always ok; git state changes require permission
- [GT1c] Don't skip hooks; no `--no-verify`; no AI attribution
- [GT1d] One logical change per commit; don't amend/rewrite history unless instructed

### [CC1] Clean Code & Architecture

- [CC1a] Clean Code + DDD are mandatory
- [CC1b] DRY: remove duplication
- [CC1c] YAGNI: no speculative abstractions—earn complexity with proven need
- [CC1d] Clean Architecture: dependencies point inward; domain is framework-free
- Contract: `docs/contracts/project-code-requirements.md`

### [ID1] Idiomatic Patterns

- [ID1a] Prefer idiomatic/default platform patterns (Weave ops, LangGraph state)
- [ID1b] Custom patterns require strong justification
- [ID1c] Don't reinvent: use Weave objects for observability, LangGraph for state/orchestration
- [ID1d] Don't assume library behavior; confirm correct usage via docs
- Contract: `docs/contracts/project-code-requirements.md`

### [FS1] File & Structure Standards

- [FS1a] Before creating anything: search/reuse first; don't duplicate logic
- [FS1b] Type safety: use Pydantic models and typed protocols; no `dict[str, Any]` in domain
- [FS1c] No dead code; no bare `except:` blocks
- [FS1d] Domain stays framework-free (per [CC1d])
- [FS1e] Prefer existing utilities; no redundant wrappers
- [FS1f] When touching large files, extract a seam; don't grow monoliths
- [FS1g] No generic `*_utils/*_helper/*_common` grab bags
- Contract: `docs/contracts/project-code-requirements.md`

### [MO1] Modularity & SRP

- [MO1a] No monoliths: avoid multi-concern files and catch-all modules
- [MO1b] New work starts in new files; when touching a monolith, extract at least one seam
- [MO1c] If you can't reduce safely in this change, stop and surface the constraint
- [MO1d] Strict SRP: each class/function is "about one thing" and has one reason to change
- [MO1e] Boundary rule: cross-module interaction happens only through explicit, typed contracts
- [MO1f] Decision Logic: New feature → New file; Bug fix → Edit existing; Logic change → Extract/Replace
- Contract: `docs/contracts/project-code-requirements.md`

### [ND1] Naming & Intent

- [ND1a] Intent-revealing names only
- [ND1b] Ban generic names (`data`, `info`, `value`, `item`, `obj`, `tmp`, etc.)
- [ND1c] When touching legacy generic names, fix them in the same edit
- Contract: `docs/contracts/project-code-requirements.md`

### [AB1] Abstraction Quality

- [AB1a] No anemic wrappers/forwarders
- [AB1b] New abstractions must earn reuse by removing real duplication
- [AB1c] Delete unused code instead of keeping "just in case"
- Contract: `docs/contracts/project-code-requirements.md`

### [RC1] No Silent Failures

- [RC1a] No silent fallback/degradation paths
- [RC1b] Investigate → understand → fix; no workarounds
- [RC1c] Use typed exception handling; don't swallow root causes
- [RC1d] Absolute ban on shims/workarounds to silence failures; fix at source or halt
- Contract: `docs/contracts/project-code-requirements.md`

### [WV1] Weave Integration

- [WV1a] Use `@weave.op()` for all LLM calls and agent operations
- [WV1b] Use Weave objects for persistent state (memory, feedback, rankings)
- [WV1c] Traces are the primary observability layer; don't build custom logging
- [WV1d] Use Weave's evaluation patterns for agent quality assessment
- Contract: `docs/contracts/weave-integration.md`

### [LG1] LangGraph Integration

- [LG1a] Use LangGraph StateGraph for orchestration; don't build custom state machines
- [LG1b] Agent state is a TypedDict or Pydantic model; no loose dicts
- [LG1c] Use LangGraph's built-in patterns for sub-agents and conditional routing
- [LG1d] Thread persistence uses LangGraph checkpointing
- Contract: `docs/contracts/langgraph-state.md`

### [LM1] LLM Provider Abstraction

- [LM1a] Support OpenAI Responses API for structured output
- [LM1b] Support Chat Completions API for OpenAI-compatible endpoints
- [LM1c] Provider abstraction via protocol/interface in domain layer
- [LM1d] Adapter implementations in `adapters/llm/`
- Contract: `docs/contracts/llm-providers.md`

### [AP1] API & Exposure

- [AP1a] FastAPI for REST API; auto-generate OpenAPI spec
- [AP1b] MCP server for TUI/tool-call consumers (Claude Code, etc.)
- [AP1c] Python package interface for direct library use
- [AP1d] Orval generates TypeScript types from OpenAPI
- Contract: `docs/api-contracts/openapi.md`

### [AR1] Architecture Layers

- [AR1a] Canonical roots only: `domain/`, `adapters/`, `application/`, `api/`, `graph/`, `mcp/`
- [AR1b] Domain is framework-free; no FastAPI/Weave/LangGraph imports (Exception: `langchain_core` messages/runnables are allowed primitives)
- [AR1c] Adapters implement domain protocols; one adapter per external system
- [AR1d] Application layer contains use cases; orchestrates domain + adapters
- [AR1e] Flow: api/mcp → application → domain → adapters
- Contract: `docs/contracts/project-code-requirements.md`

### [TS1] Testing Standards

- [TS1a] Add/maintain tests for new functionality
- [TS1b] Assert observable behavior, not internals
- [TS1c] Use Weave evaluation for agent quality testing
- [TS1d] Naming: `test_{module}.py` with `test_{function}` functions

### [VR1] Verification Gates

- [VR1a] Run `make validate` before any commit
- [VR1b] Gates: Format check, Lint, Type check, Arch tests, Unit tests
- Contract: `docs/contracts/project-code-requirements.md`
