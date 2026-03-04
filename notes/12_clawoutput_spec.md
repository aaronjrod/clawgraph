# ClawOutput Formal Specification

> **Status**: Canonical  
> **Resolves**: Appendix §2.2 (`ClawOutput Formal Specification` gap)  
> **Ref**: [03_FRS.md](file:///Users/aaronrodrigues/projects/clawgraph/notes/03_FRS.md), [06_patterns.md](file:///Users/aaronrodrigues/projects/clawgraph/notes/06_patterns.md), [10_clawnode_spec.md](file:///Users/aaronrodrigues/projects/clawgraph/notes/10_clawnode_spec.md)

---

## 1. Overview

`ClawOutput` is the single most load-bearing data structure in ClawGraph. Every node produces one, and both the Orchestrator and Signal Manager consume it. This document is the canonical definition — all other documents should cross-reference here rather than redefining the schema inline.

### 1.1 Core Tension

ClawOutput serves two consumers with different needs:

| Consumer | Needs | Risk if over-served |
| :--- | :--- | :--- |
| **Orchestrator** | Terse signal + summary + pointer. Just enough to route. | Context bloat undermines token efficiency. |
| **Signal Manager / Timeline** | Full fidelity. Everything, forever. | N/A — storage is cheap, audit is priceless. |

### 1.2 Solution: Two-Layer Schema

The model is structured as a **routing envelope** (always visible to the Orchestrator) and a **detail payload** (persisted to the timeline but not injected into the Orchestrator's active context unless explicitly requested via `audit_node()`).

The Orchestrator receives the full object but is instructed to reason only over the envelope fields. The Signal Manager persists the full object.

---

## 2. Enums

```python
from enum import Enum

class Signal(str, Enum):
    """Terminal signal emitted by every ClawNode."""
    DONE               = "DONE"
    FAILED             = "FAILED"
    PARTIAL            = "PARTIAL"
    NEED_INFO          = "NEED_INFO"
    HOLD_FOR_HUMAN     = "HOLD_FOR_HUMAN"
    NEED_INTERVENTION  = "NEED_INTERVENTION"


class FailureClass(str, Enum):
    """Categorizes the root cause of a FAILED or PARTIAL signal. (F-REQ-7)"""
    LOGIC_ERROR          = "LOGIC_ERROR"
    SCHEMA_MISMATCH      = "SCHEMA_MISMATCH"
    TOOL_FAILURE         = "TOOL_FAILURE"
    GUARDRAIL_VIOLATION  = "GUARDRAIL_VIOLATION"
    SYSTEM_CRASH         = "SYSTEM_CRASH"
```

---

## 3. Sub-Models

```python
from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional
from uuid import uuid4


class ErrorDetail(BaseModel):
    """Structured error payload. Required on FAILED, PARTIAL (with failed branches),
    and NEED_INTERVENTION signals. (F-REQ-7, F-REQ-8)"""
    failure_class: FailureClass
    message: str                                  # Human-readable error description.
    expected: Optional[str] = None                # What the node expected (if applicable).
    actual: Optional[str] = None                  # What actually happened (if applicable).
    suggested_fix_hint: Optional[str] = None      # Plain-language fix hint for SO repair logic.
    traceback: Optional[str] = None               # Python traceback. Populated on SYSTEM_CRASH
                                                  # or when orchestrator_synthesized=True.


class InfoRequest(BaseModel):
    """Payload for NEED_INFO signals. The node is suspended and awaiting clarification. (F-REQ-6)"""
    question: str                                 # What the node needs to know.
    context: str                                  # Why it needs to know — enough for the
                                                  # target to answer without auditing the node.
    target: str = "SO"                            # "SO" | "USER" | "EITHER"


class HumanRequest(BaseModel):
    """Payload for HOLD_FOR_HUMAN signals. Must be self-contained — assume the
    human has no prior context. (F-REQ-26)"""
    message: str                                  # The complete request for the human.
    action_type: Optional[str] = None             # e.g., "approve_shell", "review_diff",
                                                  # "legal_sign_off". Helps the delivery
                                                  # layer render the right UI.


class BranchResult(BaseModel):
    """Per-branch outcome within an Aggregator's ClawOutput. (F-REQ-13)"""
    branch_id: str
    node_id: str
    signal: Signal
    summary: str
    result_uri: Optional[str] = None
    error_detail: Optional[ErrorDetail] = None
```

---

## 4. ClawOutput (Canonical Model)

```python
from pydantic import model_validator


class ClawOutput(BaseModel):
    """
    The universal output contract for every ClawNode.

    ROUTING ENVELOPE (Orchestrator reads these):
        signal, node_id, orchestrator_summary, result_uri, audit_hint, orchestrator_synthesized

    DETAIL PAYLOAD (Timeline persists these; Orchestrator ignores unless auditing):
        operator_summary, error_detail, info_request, human_request, continuation_context,
        started_at, completed_at, raw_tool_outputs

    INFRASTRUCTURE:
        schema_version, output_id
    """

    # ── Infrastructure ─────────────────────────────────────────────
    schema_version: int = 1                       # Increment on breaking schema changes.
                                                  # See §6 (Versioning Strategy).
    output_id: str = Field(                       # UUID for idempotency. Prevents duplicate
        default_factory=lambda: str(uuid4())      # processing on LangGraph checkpoint replay.
    )                                             # See §5.3.

    # ── Routing Envelope ───────────────────────────────────────────
    signal: Signal                                # Terminal signal. Drives all routing.
    node_id: str                                  # ID of the emitting node.
    orchestrator_summary: str                     # Terse, routing-relevant summary (1-2 sentences).
                                                  # Should answer: "did this succeed, and what is
                                                  # the key output?" for the Orchestrator.
    result_uri: Optional[str] = None              # Pointer to artifact in Document Archive.
                                                  # REQUIRED for DONE and PARTIAL.
                                                  # See §5.4 for null semantics.
    audit_hint: Optional[bool] = None             # True = node self-flags for deeper critique.
                                                  # None = node didn't set it (not the same as False).
                                                  # False = node explicitly decided no audit needed.
                                                  # Policy > Hint (F-REQ-27).
    orchestrator_synthesized: bool = False         # True = the node never returned a ClawOutput;
                                                  # the Orchestrator constructed this from wreckage.
                                                  # This is a PROVENANCE marker, not a behavioral
                                                  # hint. See §5.2.

    # ── Detail Payload ─────────────────────────────────────────────
    operator_summary: Optional[str] = None        # Human-readable summary for HUD/visualization.
                                                  # If None, the HUD falls back to orchestrator_summary.
    error_detail: Optional[ErrorDetail] = None    # Structured error. Required on FAILED/PARTIAL
                                                  # (with failures)/NEED_INTERVENTION.
    info_request: Optional[InfoRequest] = None    # Required on NEED_INFO.
    human_request: Optional[HumanRequest] = None  # Required on HOLD_FOR_HUMAN.
    continuation_context: Optional[dict] = None   # Opaque state for resumption on NEED_INFO /
                                                  # HOLD_FOR_HUMAN. Allows the node to resume
                                                  # from where it left off rather than re-running
                                                  # from scratch. See §5.5.
    started_at: Optional[datetime] = None         # Self-reported execution start time.
    completed_at: Optional[datetime] = None       # Self-reported execution end time.
                                                  # Both are optional because synthesized outputs
                                                  # may not have reliable timing.

    # ── Validators ─────────────────────────────────────────────────

    @model_validator(mode="after")
    def validate_signal_requirements(self) -> "ClawOutput":
        """Enforce signal-conditional field requirements at instantiation."""

        if self.signal == Signal.FAILED:
            if self.error_detail is None:
                raise ValueError("FAILED signal requires error_detail.")

        if self.signal == Signal.PARTIAL:
            if self.result_uri is None:
                raise ValueError("PARTIAL signal requires result_uri (partial artifacts must be committed).")

        if self.signal == Signal.DONE:
            if self.result_uri is None:
                raise ValueError("DONE signal requires result_uri (what did the node produce?).")

        if self.signal == Signal.NEED_INFO:
            if self.info_request is None:
                raise ValueError("NEED_INFO signal requires info_request payload.")

        if self.signal == Signal.HOLD_FOR_HUMAN:
            if self.human_request is None:
                raise ValueError("HOLD_FOR_HUMAN signal requires human_request payload.")

        if self.signal == Signal.NEED_INTERVENTION:
            if self.error_detail is None:
                raise ValueError("NEED_INTERVENTION signal requires error_detail (what drifted?).")

        return self
```

---

## 5. AggregatorOutput (Subclass)

Aggregator nodes produce a `ClawOutput` that describes what a *set of branches* did, not what a single node did. The semantics of shared fields diverge enough to warrant a dedicated subclass.

```python
class AggregatorOutput(ClawOutput):
    """
    Extended output for Aggregator nodes within a Signal Bubble. (F-REQ-13)

    Overridden semantics:
        - node_id: The Aggregator's own ID (NOT the subgraph's ID).
        - result_uri: Points to the Aggregator's merged artifact or a manifest
          of branch URIs — never a single branch artifact.
        - orchestrator_summary: The Aggregator's synthesis of branch outcomes,
          not a concatenation of branch summaries.
    """
    branch_breakdown: list[BranchResult]          # Per-branch outcomes. Always populated.
    partial_commit_policy: str = "eager"          # "eager" | "atomic". (F-REQ-13)

    @model_validator(mode="after")
    def validate_aggregator_requirements(self) -> "AggregatorOutput":
        if not self.branch_breakdown:
            raise ValueError("AggregatorOutput requires at least one BranchResult.")
        return self
```

---

## 6. Design Decisions

### 5.1 Two Summaries, Not One

The original `summary` field served four consumers with different needs:

| Consumer | Needs |
| :--- | :--- |
| Orchestrator | Terse, routing-relevant |
| Super-Orchestrator | Diagnostic, repair-relevant |
| HUD / Visualization | Human-readable at a glance |
| Timeline / Search | Stable, searchable |

`orchestrator_summary` optimizes for the Orchestrator (terse routing). `operator_summary` optimizes for the HUD (human-readable). The SO gets both. The timeline persists both.

If `operator_summary` is None, the HUD falls back to `orchestrator_summary`. Node authors only *need* to write one summary — the second is optional polish.

### 5.2 `orchestrator_synthesized` Is a Provenance Marker

The flag means "the node never returned a ClawOutput at all — the Orchestrator constructed this from wreckage." It does NOT drive behavioral differences in the SO's repair strategy. The `failure_class` enum (`SYSTEM_CRASH` vs `LOGIC_ERROR` etc.) carries the behavioral signal.

**Rationale**: A synthesized crash is more likely a bug in the node *implementation*, while a node-returned `FAILED` might be a logic or tool issue. But that distinction belongs in `failure_class`, not in a boolean flag. The flag's only job is provenance — "who authored this output?"

### 5.3 `output_id` for Idempotency

LangGraph checkpoints state and can replay nodes on resume. Without a unique `output_id`, the Signal Manager may receive duplicate `ClawOutput` emissions on replay. The Orchestrator and Signal Manager should deduplicate on `output_id`.

### 5.4 `result_uri` Null Semantics

| Signal | `result_uri` | Meaning |
| :--- | :--- | :--- |
| `DONE` | **Required** | What was produced. |
| `PARTIAL` | **Required** | What was partially produced. |
| `FAILED` | `None` | Nothing was produced. |
| `NEED_INFO` | `None` | Work is suspended, no artifact yet. |
| `HOLD_FOR_HUMAN` | `None` | Work is suspended, no artifact yet. |
| `NEED_INTERVENTION` | Optional | May include a diagnostic artifact. |

### 5.5 `continuation_context` for Stateful Resumption

When a node emits `NEED_INFO` or `HOLD_FOR_HUMAN`, it's *suspended*, not *done*. The node expects a response and wants to continue from where it left off.

`continuation_context` is an opaque `dict` that the node populates with whatever state it needs to resume. On `resume_job()`, this context is injected back into the node's state. Without it, resumption requires re-running the node from scratch — wasteful and potentially non-idempotent.

**The contract**: Nodes are stateless *functions* but can opt into checkpoint-based resumption via `continuation_context`. The runtime manages persistence; the node just says what it needs.

### 5.6 `audit_hint` Is a `bool`, Not a `str`

The original spec (`06_patterns.md`) typed `audit_hint` as `str | None`, which conflates the flag with a message. The canonical type is `Optional[bool]` with three-valued semantics:
- `True`: Node self-flags for audit
- `False`: Node explicitly opts out
- `None`: Node didn't express a preference (defer to `audit_policy`)

If the node wants to *explain* why it flagged for audit, that goes in `orchestrator_summary`.

---

## 7. Versioning Strategy

`schema_version` is an integer that increments on breaking changes to the ClawOutput model.

| Scenario | Orchestrator Behavior |
| :--- | :--- |
| `output.schema_version == current` | Process normally. |
| `output.schema_version < current` | Attempt coercion via a registered migration function. If no migration exists, emit a `SCHEMA_MISMATCH` `failure_class` to the SO. |
| `output.schema_version > current` | Reject. The Orchestrator cannot process a future schema. Emit `NEED_INTERVENTION`. |

**Why this matters**: The Super-Orchestrator can update nodes mid-job via CRUD operations (F-REQ-1). A node written against v1 may emit output consumed by an Orchestrator running v2. Version skew can happen *within a single execution*.

---

## 8. The Three-Type Distinction

The spec currently conflates three related but distinct data types:

| Type | Producer | Consumer | Persistence |
| :--- | :--- | :--- | :--- |
| **ClawOutput** | Nodes | Orchestrator, Signal Manager | Timeline (durable) |
| **Orchestrator Status Event** | Orchestrator | Signal Manager | HUD (transient) + optionally Timeline |
| **Timeline Event** | Signal Manager (transforms ClawOutput + Status Events) | `get_timeline()` API | Session DB (durable) |

`ClawOutput` is the node contract defined here. Orchestrator status events (`STALLED`, `RUNNING`, `RESOLVING`) are a separate, simpler schema — they are internal bookkeeping, not node outputs. Timeline events (F-REQ-31) are the persistence schema that maps *both* ClawOutputs and status events into a unified `{event_id, timestamp, node_id, signal, summary, duration_ms, tier, metadata}` record.

The Signal Manager is responsible for the transformation from ClawOutput → Timeline Event. The mapping of fields (`orchestrator_summary` → `summary`, `completed_at - started_at` → `duration_ms`, etc.) should be codified in the Signal Manager's implementation, not left implicit.

---

**Ref**: [03_FRS.md](file:///Users/aaronrodrigues/projects/clawgraph/notes/03_FRS.md), [05_ARCHITECTURE.md](file:///Users/aaronrodrigues/projects/clawgraph/notes/05_ARCHITECTURE.md), [06_patterns.md](file:///Users/aaronrodrigues/projects/clawgraph/notes/06_patterns.md), [10_clawnode_spec.md](file:///Users/aaronrodrigues/projects/clawgraph/notes/10_clawnode_spec.md)
