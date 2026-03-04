"""
ClawOutput and related Pydantic models — the canonical schema for ClawGraph.

This module implements the models defined in 12_clawoutput_spec.md.
Every ClawNode produces a ClawOutput; both the Orchestrator and Signal Manager consume it.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Optional
from uuid import uuid4

from pydantic import BaseModel, Field, model_validator


# ── Enums ──────────────────────────────────────────────────────────────────────


class Signal(str, Enum):
    """Terminal signal emitted by every ClawNode."""

    DONE = "DONE"
    FAILED = "FAILED"
    PARTIAL = "PARTIAL"
    NEED_INFO = "NEED_INFO"
    HOLD_FOR_HUMAN = "HOLD_FOR_HUMAN"
    NEED_INTERVENTION = "NEED_INTERVENTION"


class FailureClass(str, Enum):
    """Categorizes the root cause of a FAILED or PARTIAL signal. (F-REQ-7)"""

    LOGIC_ERROR = "LOGIC_ERROR"
    SCHEMA_MISMATCH = "SCHEMA_MISMATCH"
    TOOL_FAILURE = "TOOL_FAILURE"
    GUARDRAIL_VIOLATION = "GUARDRAIL_VIOLATION"
    SYSTEM_CRASH = "SYSTEM_CRASH"


# ── Sub-Models ─────────────────────────────────────────────────────────────────


class ErrorDetail(BaseModel):
    """Structured error payload.

    Required on FAILED, PARTIAL (with failed branches), and NEED_INTERVENTION
    signals. (F-REQ-7, F-REQ-8)
    """

    failure_class: FailureClass
    message: str  # Human-readable error description.
    expected: Optional[str] = None  # What the node expected (if applicable).
    actual: Optional[str] = None  # What actually happened (if applicable).
    suggested_fix_hint: Optional[str] = None  # Plain-language fix hint for SO repair.
    traceback: Optional[str] = None  # Python traceback. Populated on SYSTEM_CRASH.


class InfoRequest(BaseModel):
    """Payload for NEED_INFO signals.

    The node is suspended and awaiting clarification. (F-REQ-6)
    """

    question: str  # What the node needs to know.
    context: str  # Why it needs to know — enough for the target to answer.
    target: str = "SO"  # "SO" | "USER" | "EITHER"


class HumanRequest(BaseModel):
    """Payload for HOLD_FOR_HUMAN signals.

    Must be self-contained — assume the human has no prior context. (F-REQ-26)
    """

    message: str  # The complete request for the human.
    action_type: Optional[str] = None  # e.g., "approve_shell", "review_diff"


class BranchResult(BaseModel):
    """Per-branch outcome within an Aggregator's ClawOutput. (F-REQ-13)"""

    branch_id: str
    node_id: str
    signal: Signal
    summary: str
    result_uri: Optional[str] = None
    error_detail: Optional[ErrorDetail] = None


# ── ClawOutput (Canonical Model) ──────────────────────────────────────────────


class ClawOutput(BaseModel):
    """The universal output contract for every ClawNode.

    ROUTING ENVELOPE (Orchestrator reads these):
        signal, node_id, orchestrator_summary, result_uri,
        audit_hint, orchestrator_synthesized

    DETAIL PAYLOAD (Timeline persists these; Orchestrator ignores unless auditing):
        operator_summary, error_detail, info_request, human_request,
        continuation_context, started_at, completed_at

    INFRASTRUCTURE:
        schema_version, output_id
    """

    # ── Infrastructure ─────────────────────────────────────────────
    schema_version: int = 1
    output_id: str = Field(default_factory=lambda: str(uuid4()))

    # ── Routing Envelope ───────────────────────────────────────────
    signal: Signal
    node_id: str
    orchestrator_summary: str
    result_uri: Optional[str] = None
    audit_hint: Optional[bool] = None
    orchestrator_synthesized: bool = False

    # ── Detail Payload ─────────────────────────────────────────────
    operator_summary: Optional[str] = None
    error_detail: Optional[ErrorDetail] = None
    info_request: Optional[InfoRequest] = None
    human_request: Optional[HumanRequest] = None
    continuation_context: Optional[dict] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

    # ── Validators ─────────────────────────────────────────────────

    @model_validator(mode="after")
    def validate_signal_requirements(self) -> ClawOutput:
        """Enforce signal-conditional field requirements at instantiation."""
        if self.signal == Signal.FAILED:
            if self.error_detail is None:
                raise ValueError("FAILED signal requires error_detail.")

        if self.signal == Signal.PARTIAL:
            if self.result_uri is None:
                raise ValueError(
                    "PARTIAL signal requires result_uri "
                    "(partial artifacts must be committed)."
                )

        if self.signal == Signal.DONE:
            if self.result_uri is None:
                raise ValueError(
                    "DONE signal requires result_uri "
                    "(what did the node produce?)."
                )

        if self.signal == Signal.NEED_INFO:
            if self.info_request is None:
                raise ValueError("NEED_INFO signal requires info_request payload.")

        if self.signal == Signal.HOLD_FOR_HUMAN:
            if self.human_request is None:
                raise ValueError(
                    "HOLD_FOR_HUMAN signal requires human_request payload."
                )

        if self.signal == Signal.NEED_INTERVENTION:
            if self.error_detail is None:
                raise ValueError(
                    "NEED_INTERVENTION signal requires error_detail "
                    "(what drifted?)."
                )

        return self


# ── AggregatorOutput (Subclass) ───────────────────────────────────────────────


class AggregatorOutput(ClawOutput):
    """Extended output for Aggregator nodes within a Signal Bubble. (F-REQ-13)

    Overridden semantics:
        - node_id: The Aggregator's own ID (NOT the subgraph's ID).
        - result_uri: Points to the merged artifact or manifest of branch URIs.
        - orchestrator_summary: Synthesis of branch outcomes.
    """

    branch_breakdown: list[BranchResult]
    partial_commit_policy: str = "eager"  # "eager" | "atomic"

    @model_validator(mode="after")
    def validate_aggregator_requirements(self) -> AggregatorOutput:
        """Aggregators must report at least one branch result."""
        if not self.branch_breakdown:
            raise ValueError(
                "AggregatorOutput requires at least one BranchResult."
            )
        return self
