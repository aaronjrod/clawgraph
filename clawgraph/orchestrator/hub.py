"""Orchestrator hub logic — the central LangGraph node and graph builder.

The Orchestrator node sits at the center of the hub-and-spoke topology.
It receives signals from nodes, decides what happens next, and dispatches
the next node. It also handles exception interception, prerequisite
checking, and iteration governance.

Architecture ref: 05_ARCHITECTURE.md §4, §6
"""

from __future__ import annotations

import logging
import traceback
from collections.abc import Callable
from typing import Any

from langgraph.graph import END, StateGraph

from clawgraph.bag.manager import BagManager
from clawgraph.core.models import (
    ClawOutput,
    ErrorDetail,
    FailureClass,
    Signal,
)
from clawgraph.core.signals import SignalManager
from clawgraph.orchestrator.graph import BagState

logger = logging.getLogger(__name__)


# ── Signal Routing (Conditional Edges) ────────────────────────────────────────


# Routing outcomes — these are the LangGraph edge target names.
ROUTE_NEXT_NODE = "dispatch_node"
ROUTE_ESCALATE = "escalate"
ROUTE_SUSPEND = "suspend"
ROUTE_COMPLETE = "complete"


def route_signal(state: BagState) -> str:
    """Conditional edge function: maps the current signal to the next step.

    This is the Orchestrator's decision function — it reads current_output
    and decides the next graph transition.

    Returns:
        One of ROUTE_NEXT_NODE, ROUTE_ESCALATE, ROUTE_SUSPEND, ROUTE_COMPLETE.
    """
    output = state.get("current_output", {})
    signal = output.get("signal")
    iteration_count = state.get("iteration_count", 0)
    max_iterations = state.get("max_iterations", 10)

    # Budget exhaustion check.
    if iteration_count >= max_iterations:
        logger.warning(
            "Iteration budget exhausted (%d/%d). Escalating.",
            iteration_count,
            max_iterations,
        )
        return ROUTE_ESCALATE

    # Signal-based routing.
    if signal == Signal.DONE:
        # Check if there are more nodes to dispatch or if we're done.
        # For now, DONE from any node completes the job.
        # Phase 3+ will add multi-step planning here.
        return ROUTE_COMPLETE

    if signal in (Signal.FAILED, Signal.NEED_INTERVENTION):
        return ROUTE_ESCALATE

    if signal == Signal.NEED_INFO:
        return ROUTE_ESCALATE  # Surface to SO for clarification.

    if signal == Signal.HOLD_FOR_HUMAN:
        return ROUTE_SUSPEND

    if signal == Signal.PARTIAL:
        return ROUTE_ESCALATE  # SO decides on remediation.

    # No signal yet (first iteration) — dispatch a node.
    if signal is None:
        return ROUTE_NEXT_NODE

    # Unknown signal — escalate defensively.
    logger.warning("Unknown signal '%s'. Escalating.", signal)
    return ROUTE_ESCALATE


# ── Node Functions ────────────────────────────────────────────────────────────


def _make_dispatch_node(
    bag_manager: BagManager,
    signal_manager: SignalManager,
) -> Callable[[BagState], BagState]:
    """Create the dispatch_node function for the StateGraph.

    This node:
    1. Selects the next node to run (currently: first available).
    2. Checks prerequisites.
    3. Executes the node with exception interception.
    4. Processes the signal through the SignalManager.
    """

    def dispatch_node(state: BagState) -> BagState:
        """Execute the next node and process its output."""
        updates: dict[str, Any] = {}

        # ── Select next node ──────────────────────────────────────
        node_id = state.get("current_node_id")
        if node_id is None:
            # First dispatch — pick the first node in manifest.
            # Phase 3+ will replace this with LLM-based planning.
            manifest = state.get("bag_manifest", {})
            nodes = manifest.get("nodes", {})
            if not nodes:
                logger.warning("No nodes in manifest. Escalating.")
                updates["current_output"] = _synthesize_error(
                    node_id="__orchestrator__",
                    message="No nodes registered in the bag.",
                    failure_class=FailureClass.LOGIC_ERROR,
                )
                updates["pending_escalation"] = updates["current_output"]
                return updates  # type: ignore[return-value]
            node_id = next(iter(nodes))

        updates["current_node_id"] = node_id

        # ── Check prerequisites ───────────────────────────────────
        try:
            node_meta = bag_manager.manifest.nodes.get(node_id)
        except Exception:
            node_meta = None

        if node_meta and node_meta.requires:
            archive = state.get("document_archive", {})
            missing = [r for r in node_meta.requires if r not in archive]
            if missing:
                signal_manager.mark_stalled(node_id)
                logger.info(
                    "Node '%s' STALLED: missing prerequisites %s.",
                    node_id,
                    missing,
                )
                updates["current_output"] = {
                    "signal": Signal.NEED_INTERVENTION,
                    "node_id": node_id,
                    "orchestrator_summary": (
                        f"Node '{node_id}' is STALLED. "
                        f"Missing prerequisites: {missing}"
                    ),
                    "error_detail": {
                        "failure_class": FailureClass.LOGIC_ERROR,
                        "message": f"Unmet prerequisites: {missing}",
                    },
                    "orchestrator_synthesized": True,
                }
                updates["pending_escalation"] = updates["current_output"]
                return updates  # type: ignore[return-value]

        # ── Execute node (with exception interception) ────────────
        signal_manager.mark_running(node_id)

        try:
            node_fn = bag_manager.get_node_fn(node_id)
            result: ClawOutput = node_fn(state)

            # Process the signal through SignalManager.
            signal_manager.process_signal(result)

            updates["current_output"] = result.model_dump()
            updates["iteration_count"] = state.get("iteration_count", 0) + 1

            # On DONE, append to phase_history.
            if result.signal == Signal.DONE:
                history = list(state.get("phase_history", []))
                history.append(result.orchestrator_summary)
                updates["phase_history"] = history

                # Store result in document_archive if result_uri exists.
                if result.result_uri:
                    archive = dict(state.get("document_archive", {}))
                    archive[f"{node_id}_result"] = result.result_uri
                    updates["document_archive"] = archive

            # On escalation signals, set pending_escalation.
            if result.signal in (
                Signal.FAILED,
                Signal.NEED_INFO,
                Signal.NEED_INTERVENTION,
                Signal.PARTIAL,
            ):
                updates["pending_escalation"] = result.model_dump()

            # On HOLD_FOR_HUMAN, mark as suspended.
            if result.signal == Signal.HOLD_FOR_HUMAN:
                updates["suspended"] = True

            logger.info(
                "Node '%s' completed: signal=%s.",
                node_id,
                result.signal.value,
            )

        except Exception as exc:
            # ── Exception interception (F-REQ-11) ─────────────────
            logger.error(
                "Unhandled exception in node '%s': %s",
                node_id,
                exc,
                exc_info=True,
            )
            error_output = _synthesize_error(
                node_id=node_id,
                message=str(exc),
                failure_class=FailureClass.SYSTEM_CRASH,
                tb=traceback.format_exc(),
            )
            signal_manager.process_signal(
                ClawOutput(**error_output)
            )

            updates["current_output"] = error_output
            updates["pending_escalation"] = error_output
            updates["iteration_count"] = state.get("iteration_count", 0) + 1

        return updates  # type: ignore[return-value]

    return dispatch_node


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
) -> Callable[[BagState], BagState]:
    """Create the suspension node for HOLD_FOR_HUMAN signals."""

    def suspend(state: BagState) -> BagState:
        """Checkpoint and deliver the human request via the HITL handler.

        In Phase 5, this will persist the checkpoint to the Session DB.
        For now, it calls the handler (if registered) and returns.
        """
        output = state.get("current_output", {})
        thread_id = state.get("thread_id", "unknown")
        human_request = output.get("human_request", {})

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

    Returns:
        A compiled LangGraph graph.
    """
    graph = StateGraph(BagState)

    # Register nodes.
    # NOTE: type: ignore needed because LangGraph's strict overloads
    # don't fully match our closure-based node pattern.
    graph.add_node(ROUTE_NEXT_NODE, _make_dispatch_node(bag_manager, signal_manager))  # type: ignore[call-overload]
    graph.add_node(ROUTE_ESCALATE, _make_escalate_node())  # type: ignore[call-overload]
    graph.add_node(ROUTE_SUSPEND, _make_suspend_node(hitl_handler))  # type: ignore[call-overload]
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

    return graph.compile()


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
