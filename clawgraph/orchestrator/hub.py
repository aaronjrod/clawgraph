"""Orchestrator hub logic — the central LangGraph node and graph builder.

The Orchestrator node sits at the center of the hub-and-spoke topology.
It receives signals from nodes, decides what happens next, and dispatches
the next node. It also handles exception interception, prerequisite
checking, iteration governance, and the RESOLVING re-evaluation loop.

Architecture ref: 05_ARCHITECTURE.md §4, §6, §10.2
"""

from __future__ import annotations

import logging
import time
import traceback
from collections.abc import Callable
from typing import Any

from langgraph.graph import END, StateGraph

from clawgraph.bag.manager import BagManager
from clawgraph.core.models import (
    AggregatorOutput,
    ArchiveEntry,
    BagContract,
    ClawOutput,
    ErrorDetail,
    FailureClass,
    Signal,
)
from clawgraph.core.signals import SignalManager
from clawgraph.core.timeline import TimelineBuffer
from clawgraph.orchestrator.graph import BagState

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

    Gap 6 fix: DONE no longer unconditionally completes. It checks the
    ready_queue and loops back to dispatch if more nodes are available.

    Returns:
        One of ROUTE_NEXT_NODE, ROUTE_ESCALATE, ROUTE_SUSPEND, ROUTE_COMPLETE.
    """
    output = state.get("current_output", {})
    signal = output.get("signal")
    iteration_count = state.get("iteration_count", 0)
    max_iterations = state.get("max_iterations", 10)
    ready_queue = state.get("ready_queue", [])

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
        # Gap 6 fix: only complete if ready_queue is empty.
        if ready_queue:
            return ROUTE_NEXT_NODE
        return ROUTE_COMPLETE

    if signal in (Signal.FAILED, Signal.NEED_INTERVENTION):
        return ROUTE_ESCALATE

    if signal == Signal.NEED_INFO:
        # Gap 3 (F-REQ-10): Check escalation policy before escalating.
        node_id = output.get("node_id", "")
        tracking = state.get("need_info_tracking", {})
        node_tracking = tracking.get(node_id, {})
        retries = node_tracking.get("retries", 0)
        max_retries = node_tracking.get("max_retries", 3)

        if retries < max_retries:
            # Within retry budget — re-dispatch (node stays in queue).
            return ROUTE_NEXT_NODE
        # Budget exhausted — escalate.
        logger.warning(
            "NEED_INFO retries exhausted for '%s' (%d/%d). Promoting to NEED_INTERVENTION.",
            node_id,
            retries,
            max_retries,
        )
        return ROUTE_ESCALATE

    if signal == Signal.HOLD_FOR_HUMAN:
        return ROUTE_SUSPEND

    if signal == Signal.PARTIAL:
        return ROUTE_ESCALATE  # SO decides on remediation.

    # No signal yet (first iteration) — dispatch a node.
    if signal is None:
        if ready_queue:
            return ROUTE_NEXT_NODE
        # Nothing to dispatch and nothing done yet.
        return ROUTE_COMPLETE

    # Unknown signal — escalate defensively.
    logger.warning("Unknown signal '%s'. Escalating.", signal)
    return ROUTE_ESCALATE


# ── Node Functions ────────────────────────────────────────────────────────────


def _make_dispatch_node(
    bag_manager: BagManager,
    signal_manager: SignalManager,
    contract: BagContract | None = None,
) -> Callable[[BagState], BagState]:
    """Create the dispatch_node function for the StateGraph.

    Gap 6 fix: Pops from ready_queue instead of using current_node_id.
    Gap 1 fix: After DONE, re-evaluates stalled_queue (RESOLVING loop).
    Gap 4 fix: Respects partial_commit_policy on archive writes.
    """

    def dispatch_node(state: BagState) -> BagState:
        """Execute the next node from ready_queue and process its output."""
        updates: dict[str, Any] = {}

        # ── Pop next node from ready_queue ─────────────────────────
        ready_queue = list(state.get("ready_queue", []))
        stalled_queue = list(state.get("stalled_queue", []))
        completed_nodes = list(state.get("completed_nodes", []))

        if not ready_queue:
            # Nothing to dispatch — should have been caught by route_signal.
            logger.warning("dispatch_node called with empty ready_queue.")
            updates["current_output"] = _synthesize_error(
                node_id="__orchestrator__",
                message="No nodes in ready_queue.",
                failure_class=FailureClass.LOGIC_ERROR,
            )
            updates["pending_escalation"] = updates["current_output"]
            return updates  # type: ignore[return-value]

        node_id = ready_queue.pop(0)
        updates["current_node_id"] = node_id
        updates["ready_queue"] = ready_queue

        # ── Check prerequisites (should be satisfied, but verify) ──
        try:
            node_meta = bag_manager.manifest.nodes.get(node_id)
        except Exception:
            node_meta = None

        if node_meta and node_meta.requires:
            archive = state.get("document_archive", {})
            bag_name = state.get("bag_name", "")
            missing = [
                r for r in node_meta.requires
                if not _is_visible(archive.get(r), bag_name)
            ]
            if missing:
                # Gap 1 fix: Move to stalled_queue, NOT NEED_INTERVENTION.
                signal_manager.mark_stalled(node_id)
                logger.info(
                    "Node '%s' STALLED: missing prerequisites %s.",
                    node_id,
                    missing,
                )
                stalled_queue.append(node_id)
                updates["stalled_queue"] = stalled_queue

                # Emit STALLED event to in-state timeline.
                timeline = list(state.get("timeline", []))
                timeline.append({
                    "node_id": node_id,
                    "signal": "STALLED",
                    "summary": f"Missing: {missing}",
                })
                updates["timeline"] = timeline

                # Synthesize a status event for the timeline, but don't
                # terminate the job. Continue to the next ready node.
                if ready_queue:
                    # There are other nodes to try — recurse by setting
                    # current_output to None so route_signal dispatches again.
                    updates["current_output"] = {
                        "signal": None,
                        "node_id": node_id,
                        "orchestrator_summary": (
                            f"Node '{node_id}' stalled on {missing}. "
                            f"Trying next ready node."
                        ),
                    }
                else:
                    # No more ready nodes and this one is stalled.
                    # Check if any stalled node is a dead-end (producer FAILED).
                    updates["current_output"] = {
                        "signal": Signal.NEED_INTERVENTION,
                        "node_id": node_id,
                        "orchestrator_summary": (
                            f"Node '{node_id}' is STALLED. "
                            f"Missing prerequisites: {missing}. "
                            f"No ready nodes remain."
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

            # BagContract signal validation (F-REQ-25).
            if (
                contract
                and contract.allowed_signals is not None
                and result.signal not in contract.allowed_signals
            ):
                logger.warning(
                    "CONTRACT VIOLATION: node '%s' emitted %s, "
                    "allowed: %s. Synthesizing FAILED.",
                    node_id, result.signal.value,
                    [s.value for s in contract.allowed_signals],
                )
                result = ClawOutput(
                    signal=Signal.FAILED,
                    node_id=node_id,
                    orchestrator_summary=(
                        f"Contract violation: signal {result.signal.value} "
                        f"not in allowed_signals."
                    ),
                    orchestrator_synthesized=True,
                    error_detail=ErrorDetail(
                        failure_class=FailureClass.SCHEMA_MISMATCH,
                        message=(
                            f"Signal {result.signal.value} not permitted by "
                            f"BagContract."
                        ),
                    ),
                )
                signal_manager.process_signal(result)

            updates["current_output"] = result.model_dump()
            updates["iteration_count"] = state.get("iteration_count", 0) + 1

            # On DONE, run the RESOLVING loop (Gap 1 / F-REQ-34).
            if result.signal == Signal.DONE:
                history = list(state.get("phase_history", []))
                history.append(result.orchestrator_summary)
                updates["phase_history"] = history

                # Store result in document_archive if result_uri exists.
                archive = dict(state.get("document_archive", {}))
                if result.result_uri:
                    archive[f"{node_id}_result"] = ArchiveEntry(
                        uri=result.result_uri,
                        domain=state.get("bag_name", ""),
                        tags=["public"],
                        created_by=node_id,
                    ).model_dump()
                    updates["document_archive"] = archive

                # Mark node as completed.
                completed_nodes.append(node_id)
                updates["completed_nodes"] = completed_nodes

                # ── RESOLVING: re-evaluate stalled_queue ──────────
                newly_ready, still_stalled = _resolve_stalled(
                    stalled_queue, archive, bag_manager,
                    bag_name=state.get("bag_name", ""),
                )
                if newly_ready:
                    ready_queue = list(updates.get("ready_queue", ready_queue))
                    ready_queue.extend(newly_ready)
                    updates["ready_queue"] = ready_queue
                    logger.info(
                        "RESOLVING: %d node(s) moved from stalled to ready: %s",
                        len(newly_ready),
                        newly_ready,
                    )

                    # Emit RESOLVING event to in-state timeline.
                    timeline = list(state.get("timeline", []))
                    timeline = list(updates.get("timeline", timeline))
                    timeline.append({
                        "node_id": node_id,
                        "signal": "RESOLVING",
                        "summary": f"Unblocked: {newly_ready}",
                    })
                    updates["timeline"] = timeline

                updates["stalled_queue"] = still_stalled

            # Gap 4: Handle PARTIAL w/ partial_commit_policy.
            if result.signal == Signal.PARTIAL and isinstance(result, AggregatorOutput):
                archive = dict(state.get("document_archive", {}))
                archive = dict(updates.get("document_archive", archive))
                if result.partial_commit_policy == "eager":
                    # Commit successful branch results immediately.
                    for br in result.branch_breakdown or []:
                        if br.signal == Signal.DONE and br.result_uri:
                            archive[f"{br.branch_id}_result"] = ArchiveEntry(
                                uri=br.result_uri,
                                domain=state.get("bag_name", ""),
                                tags=["public"],
                                created_by=br.node_id,
                            ).model_dump()
                    updates["document_archive"] = archive

                    # PARTIAL+eager resolve (Appendix §1.9):
                    # Trigger stalled re-eval after eager commits.
                    newly_ready, still_stalled = _resolve_stalled(
                        stalled_queue, archive, bag_manager,
                        bag_name=state.get("bag_name", ""),
                    )
                    if newly_ready:
                        rq = list(updates.get("ready_queue", ready_queue))
                        rq.extend(newly_ready)
                        updates["ready_queue"] = rq
                        timeline = list(state.get("timeline", []))
                        timeline = list(updates.get("timeline", timeline))
                        timeline.append({
                            "node_id": node_id,
                            "signal": "RESOLVING",
                            "summary": f"PARTIAL eager unblocked: {newly_ready}",
                        })
                        updates["timeline"] = timeline
                    updates["stalled_queue"] = still_stalled

                # "atomic" -> don't commit branch results on PARTIAL.
                updates["pending_escalation"] = result.model_dump()

            # On other escalation signals, set pending_escalation.
            elif result.signal in (
                Signal.FAILED,
                Signal.NEED_INFO,
                Signal.NEED_INTERVENTION,
            ):
                updates["pending_escalation"] = result.model_dump()

                # Dead-end cascade (Appendix §1.2): when a node FAILED,
                # cascade any stalled consumers whose prereqs depend on it.
                if result.signal == Signal.FAILED:
                    cascaded, surviving = _cascade_dead_ends(
                        node_id, stalled_queue, bag_manager,
                    )
                    if cascaded:
                        completed_nodes = list(
                            updates.get("completed_nodes", completed_nodes),
                        )
                        completed_nodes.extend(cascaded)
                        updates["completed_nodes"] = completed_nodes

                        timeline = list(state.get("timeline", []))
                        timeline = list(updates.get("timeline", timeline))
                        for cid in cascaded:
                            timeline.append({
                                "node_id": cid,
                                "signal": "DEAD_END",
                                "summary": (
                                    f"Cascaded: producer '{node_id}' FAILED"
                                ),
                            })
                        updates["timeline"] = timeline
                        logger.info(
                            "DEAD_END: %d node(s) cascaded from '%s' failure: %s",
                            len(cascaded), node_id, cascaded,
                        )
                    updates["stalled_queue"] = surviving

                # Gap 3: Track NEED_INFO retries.
                if result.signal == Signal.NEED_INFO:
                    tracking = dict(state.get("need_info_tracking", {}))
                    node_track = dict(tracking.get(node_id, {
                        "retries": 0,
                        "max_retries": 3,
                        "first_seen": time.time(),
                    }))
                    node_track["retries"] = node_track.get("retries", 0) + 1
                    tracking[node_id] = node_track
                    updates["need_info_tracking"] = tracking

                    # Re-enqueue the node if within retry budget.
                    max_retries = node_track.get("max_retries", 3)
                    if node_track["retries"] < max_retries:
                        rq = list(updates.get("ready_queue", ready_queue))
                        rq.append(node_id)
                        updates["ready_queue"] = rq

            # On HOLD_FOR_HUMAN, mark as suspended.
            if result.signal == Signal.HOLD_FOR_HUMAN:
                updates["suspended"] = True

            logger.info(
                "Node '%s' completed: signal=%s.",
                node_id,
                result.signal.value,
            )

            # Audit policy enforcement (F-REQ-27, Appendix §1.3).
            # Policy > hint: if audit_policy says always, fire regardless.
            should_audit = False
            if node_meta:
                policy = (node_meta.audit_policy or {}) if node_meta.audit_policy else {}
                if policy.get("always"):
                    should_audit = True
            if not should_audit and result.audit_hint is True:
                should_audit = True
            if should_audit:
                timeline = list(state.get("timeline", []))
                timeline = list(updates.get("timeline", timeline))
                timeline.append({
                    "node_id": node_id,
                    "signal": "AUDIT_TRIGGERED",
                    "summary": f"Audit triggered for '{node_id}'",
                })
                updates["timeline"] = timeline

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


def _resolve_stalled(
    stalled_queue: list[str],
    archive: dict[str, Any],
    bag_manager: BagManager,
    bag_name: str = "",
) -> tuple[list[str], list[str]]:
    """Re-evaluate stalled nodes against the current document_archive.

    Returns (newly_ready, still_stalled).
    This is the RESOLVING step from F-REQ-34 / Architecture S10.2.
    """
    newly_ready: list[str] = []
    still_stalled: list[str] = []

    for node_id in stalled_queue:
        try:
            meta = bag_manager.manifest.nodes.get(node_id)
        except Exception:
            meta = None

        if meta and meta.requires:
            missing = [
                r for r in meta.requires
                if not _is_visible(archive.get(r), bag_name)
            ]
            if missing:
                still_stalled.append(node_id)
            else:
                newly_ready.append(node_id)
        else:
            # No prerequisites — should be ready.
            newly_ready.append(node_id)

    return newly_ready, still_stalled


def _cascade_dead_ends(
    failed_node_id: str,
    stalled_queue: list[str],
    bag_manager: BagManager,
) -> tuple[list[str], list[str]]:
    """Cascade FAILED to stalled nodes whose prereqs depend on the failed node.

    Returns (cascaded, surviving).
    This handles the dead-end scenario from Appendix §1.2.
    """
    failed_key = f"{failed_node_id}_result"
    cascaded: list[str] = []
    surviving: list[str] = []

    for node_id in stalled_queue:
        try:
            meta = bag_manager.manifest.nodes.get(node_id)
        except Exception:
            meta = None

        if meta and meta.requires and failed_key in meta.requires:
            cascaded.append(node_id)
        else:
            surviving.append(node_id)

    return cascaded, surviving


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
    graph.add_node(ROUTE_NEXT_NODE, _make_dispatch_node(bag_manager, signal_manager, contract))  # type: ignore[call-overload]
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
