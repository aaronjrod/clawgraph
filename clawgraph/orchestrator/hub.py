"""Orchestrator hub logic — the central LangGraph node and graph builder.

The Orchestrator node sits at the center of the hub-and-spoke topology.
It receives signals from nodes, decides what happens next, and dispatches
the next node. It also handles exception interception, prerequisite
checking, iteration governance, and the RESOLVING re-evaluation loop.

Architecture ref: 05_ARCHITECTURE.md §4, §6, §10.2
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from typing import Any

from langgraph.graph import END, StateGraph

from clawgraph.bag.manager import BagManager
from clawgraph.core.models import (
    BagContract,
    ClawOutput,
    ErrorDetail,
    FailureClass,
    Signal,
)
from clawgraph.core.signals import SignalManager
from clawgraph.core.timeline import TimelineBuffer
from clawgraph.orchestrator.graph import BagState
from clawgraph.orchestrator.llm_node import make_orchestrator_node

logger = logging.getLogger(__name__)


def _is_visible(entry: Any, bag_name: str) -> bool:
    """Check if a document_archive entry is visible to the given bag.

    Visibility rule (F-REQ-17):
    - Plain strings (legacy) are always visible.
    - ArchiveEntry dicts: visible if ``domain == bag_name`` or ``"public" in tags``.
    - None (missing key) -> not visible.
    """
    if entry is None:
        return False
    if isinstance(entry, str):
        return True  # Legacy format -- always visible.
    if isinstance(entry, dict):
        domain = entry.get("domain", "")
        tags = entry.get("tags", [])
        return domain == bag_name or "public" in tags
    return False


# Routing outcomes — these are the LangGraph edge target names.
ROUTE_NEXT_NODE = "dispatch_node"
ROUTE_ESCALATE = "escalate"
ROUTE_SUSPEND = "suspend"
ROUTE_COMPLETE = "complete"


def route_signal(state: BagState) -> str:
    """Conditional edge function: maps the current signal to the next step.

    In the LLM-driven Orchestrator, the LLM sets the current_output to
    DONE, HOLD_FOR_HUMAN, NEED_INTERVENTION, or None (if it simply dispatched).
    We route based on the LLM's output.
    """
    output = state.get("current_output", {})
    signal = output.get("signal")

    # Hub-and-Spoke Principle:
    # Only signals from the 'orchestrator' node itself trigger graph termination (Complete/Suspend/Escalate).
    # Signals from leaf nodes ALWAYS loop back to the orchestrator for the next turn.
    if output.get("node_id") != "orchestrator":
        return ROUTE_NEXT_NODE

    if signal == Signal.DONE:
        return ROUTE_COMPLETE

    if signal == Signal.HOLD_FOR_HUMAN:
        return ROUTE_SUSPEND

    # Support continuity after Orchestrator-level chat or metadata updates (F-REQ-MOD-03)
    if signal is None:
        return ROUTE_NEXT_NODE

    # For any other signal from the orchestrator (FAILED, NEED_INTERVENTION, etc.), escalate.
    return ROUTE_ESCALATE


# ── Node Functions ────────────────────────────────────────────────────────────


# `_make_dispatch_node` and `_resolve_stalled` have been moved to llm_tools.py


def _make_escalate_node() -> Callable[[BagState], BagState]:
    """Create the escalation node for SO-bound signal routing."""

    def escalate(state: BagState) -> BagState:
        """Pass the pending escalation to the Super-Orchestrator.

        In Phase 3+, this will invoke the SO communication channel.
        For now, it logs the escalation and terminates the job.
        """
        escalation = state.get("pending_escalation") or {}
        signal = escalation.get("signal", "UNKNOWN")
        node_id = escalation.get("node_id", "UNKNOWN")

        logger.warning(
            "ESCALATION from node '%s' (signal=%s): %s",
            node_id,
            signal,
            escalation.get("orchestrator_summary", "No summary."),
        )

        # The job terminates here. The SO reads pending_escalation
        # from the returned state.
        return {}  # Partial state update.

    return escalate


def _make_suspend_node(
    hitl_handler: Callable[..., Any] | None,
    timeline_buffer: TimelineBuffer | None = None,
) -> Callable[[BagState], BagState]:
    """Create the suspension node for HOLD_FOR_HUMAN signals.

    Gap 2 fix: Injects timeline context into the handler payload.
    """

    def suspend(state: BagState) -> BagState:
        """Checkpoint and deliver the human request via the HITL handler.

        In Phase 5, this will persist the checkpoint to the Session DB.
        For now, it calls the handler (if registered) and returns.
        """
        output = state.get("current_output", {})
        thread_id = state.get("thread_id", "unknown")
        human_request = dict(output.get("human_request", {}))

        # Gap 2 fix (F-REQ-32): Inject timeline context.
        if timeline_buffer is not None:
            context = timeline_buffer.get_hitl_context(thread_id)
            human_request["timeline_context"] = [
                {
                    "node_id": e.node_id,
                    "signal": e.signal.value if e.signal else None,
                    "summary": e.summary,
                    "ts": e.timestamp.isoformat() if e.timestamp else None,
                }
                for e in context
            ]

        logger.info(
            "Suspending job '%s' for human input: %s",
            thread_id,
            human_request.get("message", "No message.")[:80],
        )

        if hitl_handler is not None:
            try:
                hitl_handler(thread_id, human_request)
            except Exception:
                logger.exception("HITL handler raised an exception.")
        else:
            logger.warning(
                "No HITL handler registered. Human request is in "
                "state['current_output']['human_request']."
            )

        updates: dict[str, Any] = {"suspended": True}
        return updates  # type: ignore[return-value]

    return suspend


def _make_complete_node() -> Callable[[BagState], BagState]:
    """Create the terminal completion node."""

    def complete(state: BagState) -> BagState:
        """Log job completion and finalize."""
        output = state.get("current_output", {})
        logger.info(
            "Job complete: %s",
            output.get("orchestrator_summary", "No summary."),
        )
        return {}  # Partial state update.

    return complete


# ── Graph Builder ─────────────────────────────────────────────────────────────


def build_hub_graph(
    bag_manager: BagManager,
    signal_manager: SignalManager,
    hitl_handler: Callable[..., Any] | None = None,
    timeline_buffer: TimelineBuffer | None = None,
    checkpointer: Any | None = None,
    contract: BagContract | None = None,
) -> Any:
    """Build the hub-and-spoke StateGraph for a ClawBag.

    Topology:
        START → dispatch_node → [route_signal] →
            ROUTE_NEXT_NODE → dispatch_node (loop)
            ROUTE_ESCALATE → escalate → END
            ROUTE_SUSPEND → suspend → END
            ROUTE_COMPLETE → complete → END

    Args:
        bag_manager: The BagManager with registered nodes.
        signal_manager: The SignalManager for telemetry.
        hitl_handler: Optional HITL delivery callback.
        timeline_buffer: Optional TimelineBuffer for HITL context.

    Returns:
        A compiled LangGraph graph.
    """
    graph = StateGraph(BagState)

    # Register nodes.
    # NOTE: type: ignore needed because LangGraph's strict overloads
    # don't fully match our closure-based node pattern.
    graph.add_node(ROUTE_NEXT_NODE, make_orchestrator_node(bag_manager, signal_manager, contract))
    graph.add_node(ROUTE_ESCALATE, _make_escalate_node())  # type: ignore[call-overload]
    graph.add_node(ROUTE_SUSPEND, _make_suspend_node(hitl_handler, timeline_buffer))  # type: ignore[call-overload]
    graph.add_node(ROUTE_COMPLETE, _make_complete_node())  # type: ignore[call-overload]

    # Set entry point.
    graph.set_entry_point(ROUTE_NEXT_NODE)

    # Conditional edges from dispatch_node.
    graph.add_conditional_edges(
        ROUTE_NEXT_NODE,
        route_signal,
        {
            ROUTE_NEXT_NODE: ROUTE_NEXT_NODE,
            ROUTE_ESCALATE: ROUTE_ESCALATE,
            ROUTE_SUSPEND: ROUTE_SUSPEND,
            ROUTE_COMPLETE: ROUTE_COMPLETE,
        },
    )

    # Terminal edges.
    graph.add_edge(ROUTE_ESCALATE, END)
    graph.add_edge(ROUTE_SUSPEND, END)
    graph.add_edge(ROUTE_COMPLETE, END)

    compile_kwargs: dict[str, Any] = {}
    if checkpointer is not None:
        compile_kwargs["checkpointer"] = checkpointer
    return graph.compile(**compile_kwargs)


# ── Helpers ───────────────────────────────────────────────────────────────────


def _synthesize_error(
    node_id: str,
    message: str,
    failure_class: FailureClass,
    tb: str | None = None,
) -> dict[str, Any]:
    """Build a synthesized FAILED ClawOutput dict for exception interception."""
    output = ClawOutput(
        signal=Signal.FAILED,
        node_id=node_id,
        orchestrator_summary=f"SYSTEM_CRASH in node '{node_id}': {message[:200]}",
        orchestrator_synthesized=True,
        error_detail=ErrorDetail(
            failure_class=failure_class,
            message=message,
            traceback=tb,
        ),
    )
    return output.model_dump()
