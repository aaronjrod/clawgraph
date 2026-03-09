import logging
import traceback
from typing import Any

from pydantic import BaseModel, Field

from clawgraph.bag.manager import BagManager
from clawgraph.core.models import ArchiveEntry, ClawOutput, ErrorDetail, FailureClass, Signal
from clawgraph.core.signals import SignalManager

logger = logging.getLogger(__name__)

class DispatchNodeArgs(BaseModel):
    node_id: str = Field(description="The ID of the node to execute.")

class EscalateArgs(BaseModel):
    reason: str = Field(description="The reason for escalation to the Super-Orchestrator.")
    failure_class: str = Field(description="One of: LOGIC_ERROR, SCHEMA_MISMATCH, TOOL_FAILURE, GUARDRAIL_VIOLATION, SYSTEM_CRASH")

class SuspendArgs(BaseModel):
    human_request_message: str = Field(description="The message to show the human.")

class CompleteArgs(BaseModel):
    final_summary: str = Field(description="A definitive summary of the entire completed job.")

class OrchestratorTools:
    """Tools available to the Orchestrator LLM to manage workflow state."""

    def __init__(self, bag_manager: BagManager, signal_manager: SignalManager, contract=None):
        self.bag_manager = bag_manager
        self.signal_manager = signal_manager
        self.contract = contract

    def dispatch_node(self, state: dict[str, Any], args: dict[str, Any]) -> dict[str, Any]:
        """Executes a node, processes its output, and handles state/telemetry updates."""
        node_id = args.get("node_id")
        updates = {"current_node_id": node_id}

        # Pull state vars
        stalled_queue = list(state.get("stalled_queue", []))
        completed_nodes = list(state.get("completed_nodes", []))
        ready_queue = list(state.get("ready_queue", []))

        # 1. Check Prereqs
        try:
            node_meta = self.bag_manager.manifest.nodes.get(node_id)
        except Exception:
            node_meta = None

        if node_meta and node_meta.requires:
            archive = state.get("document_archive", {})
            bag_name = state.get("bag_name", "")

            # Helper to check visibility
            def _is_visible(entry: Any, domain: str) -> bool:
                if entry is None: return False
                if isinstance(entry, str): return True
                if isinstance(entry, dict):
                    return entry.get("domain", "") == domain or "public" in entry.get("tags", [])
                return False

            missing = [r for r in node_meta.requires if not _is_visible(archive.get(r), bag_name)]
            if missing:
                self.signal_manager.mark_stalled(node_id)
                stalled_queue.append(node_id)
                updates["stalled_queue"] = stalled_queue

                timeline = []
                timeline.append({"node_id": node_id, "signal": "STALLED", "summary": f"Missing: {missing}"})
                updates["timeline"] = timeline

                updates["current_output"] = {
                    "signal": None,
                    "node_id": node_id,
                    "orchestrator_summary": f"Node '{node_id}' STALLED on missing prereqs: {missing}."
                }
                return updates

        # 2. Execute Node
        self.signal_manager.mark_running(node_id)
        try:
            node_fn = self.bag_manager.get_node_fn(node_id)
            result: ClawOutput = node_fn(state)

            # BagContract signal validation
            if (
                self.contract
                and self.contract.allowed_signals is not None
                and result.signal not in self.contract.allowed_signals
            ):
                logger.warning(
                    "CONTRACT VIOLATION: node '%s' emitted %s, allowed: %s. Synthesizing FAILED.",
                    node_id,
                    result.signal.value,
                    [s.value for s in self.contract.allowed_signals],
                )
                result = ClawOutput(
                    signal=Signal.FAILED,
                    node_id=node_id,
                    orchestrator_summary=(
                        f"Contract violation: signal {result.signal.value} not in allowed_signals."
                    ),
                    orchestrator_synthesized=True,
                    error_detail=ErrorDetail(
                        failure_class=FailureClass.SCHEMA_MISMATCH,
                        message=(f"Signal {result.signal.value} not permitted by BagContract."),
                    ),
                )

            # State drift detection
            if result.node_id != node_id:
                logger.warning(
                    "STATE DRIFT: node '%s' returned node_id='%s'. Synthesizing NEED_INTERVENTION.",
                    node_id,
                    result.node_id,
                )
                result = ClawOutput(
                    signal=Signal.NEED_INTERVENTION,
                    node_id=node_id,
                    orchestrator_summary=(
                        f"State drift: dispatched '{node_id}' but got node_id='{result.node_id}'."
                    ),
                    orchestrator_synthesized=True,
                    error_detail=ErrorDetail(
                        failure_class=FailureClass.SCHEMA_MISMATCH,
                        message=(f"Expected node_id='{node_id}', got '{result.node_id}'."),
                    ),
                )

            self.signal_manager.process_signal(result)

            updates["current_output"] = result.model_dump()
            updates["iteration_count"] = state.get("iteration_count", 0) + 1

            timeline_events = []

            if result.signal == Signal.DONE:
                history = list(state.get("phase_history", []))
                history.append(result.orchestrator_summary)
                updates["phase_history"] = [result.orchestrator_summary] # Additive state

                if result.result_uri:
                    archive = dict(state.get("document_archive", {}))
                    archive[f"{node_id}_result"] = ArchiveEntry(
                        uri=result.result_uri,
                        domain=state.get("bag_name", ""),
                        tags=["public"],
                        created_by=node_id,
                    ).model_dump()
                    updates["document_archive"] = archive

                updates["completed_nodes"] = [node_id]

            # Aggregator branch commitment logic (using model_dump to avoid slicing/class issues)
            res_dict = result.model_dump()
            branch_breakdown = res_dict.get("branch_breakdown")
            if branch_breakdown:
                archive = dict(updates.get("document_archive", state.get("document_archive", {})))
                policy = res_dict.get("partial_commit_policy", "atomic")

                for branch in branch_breakdown:
                    # branch is now a dict because res_dict is a dump
                    # branch['signal'] etc.
                    # Eager policy commits DONE branches immediately even if aggregate is PARTIAL.
                    # Atomic policy (default) only commits when the aggregate signal is DONE.
                    should_commit = False
                    b_signal = branch.get("signal")
                    if b_signal == Signal.DONE:
                        if result.signal == Signal.DONE or policy == "eager":
                            should_commit = True

                    if should_commit and branch.get("result_uri"):
                        branch_key = f"{branch.get('branch_id')}_result"
                        archive[branch_key] = ArchiveEntry(
                            uri=branch.get("result_uri"),
                            domain=state.get("bag_name", ""),
                            tags=["public"],
                            created_by=branch.get("node_id") or node_id,
                        ).model_dump()

                updates["document_archive"] = archive

            # Re-evaluate stalled queue (F-REQ-12 / RESOLVING loop)
            # If a producer just finished, some consumers might now be ready.
            new_stalled = []
            new_ready = list(updates.get("ready_queue", ready_queue))
            if node_id in new_ready:
                new_ready.remove(node_id)

            bag_name = state.get("bag_name", "")

            # Helper visibility check
            def _check_vis(entry, domain):
                if entry is None: return False
                if isinstance(entry, str): return True
                if isinstance(entry, dict):
                    return entry.get("domain", "") == domain or "public" in entry.get("tags", [])
                return False

            for stalled_id in stalled_queue:
                # Get fresh metadata (might have changed if bag was mutated)
                try:
                    meta = self.bag_manager.manifest.nodes.get(stalled_id)
                except Exception:
                    meta = None

                if not meta or not meta.requires:
                    new_ready.append(stalled_id)
                    timeline_events.append({"node_id": stalled_id, "signal": "RESOLVING", "summary": "No prerequisites found."})
                    continue

                # Check if all prereqs are now in the archive
                current_archive = updates.get("document_archive", state.get("document_archive", {}))
                missing = [r for r in meta.requires if not _check_vis(current_archive.get(r), bag_name)]

                if not missing:
                    new_ready.append(stalled_id)
                    timeline_events.append({"node_id": stalled_id, "signal": "RESOLVING", "summary": f"Prerequisites resolved: {meta.requires}"})
                else:
                    new_stalled.append(stalled_id)

            updates["stalled_queue"] = new_stalled
            updates["ready_queue"] = new_ready

            # Audit policy enforcement
            should_audit = False
            if node_meta:
                policy = (node_meta.audit_policy or {}) if node_meta.audit_policy else {}
                if policy.get("always"):
                    should_audit = True
            if not should_audit and hasattr(result, "audit_hint") and result.audit_hint is True:
                should_audit = True
            if should_audit:
                timeline_events.append(
                    {
                        "node_id": node_id,
                        "signal": "AUDIT_TRIGGERED",
                        "summary": f"Audit triggered for '{node_id}'",
                    }
                )

            if timeline_events:
                updates["timeline"] = timeline_events

            # In the LLM architecture, we return the updates, and the LLM
            # will see the current_output in the next turn to decide what to do.

        except Exception as exc:
            logger.error(f"Unhandled exception in node '{node_id}': {exc}", exc_info=True)
            error_output = {
                "signal": Signal.FAILED.value,
                "node_id": node_id,
                "orchestrator_summary": f"SYSTEM_CRASH in node '{node_id}': {str(exc)[:200]}",
                "orchestrator_synthesized": True,
                "error_detail": {
                    "failure_class": FailureClass.SYSTEM_CRASH.value,
                    "message": str(exc),
                    "traceback": traceback.format_exc()
                }
            }
            self.signal_manager.process_signal(ClawOutput(**error_output))
            updates["current_output"] = error_output
            updates["iteration_count"] = state.get("iteration_count", 0) + 1

        return updates


    def escalate(self, state: dict[str, Any], args: dict[str, Any]) -> dict[str, Any]:
        """Escalates the workflow to the human Super-Orchestrator.
        
        Also triggers DEAD_END cascading for stalled consumers if the 
        escalation is due to a terminal node failure.
        """
        reason = args.get("reason", "Unknown")
        failure_class = args.get("failure_class", "LOGIC_ERROR")
        logger.warning(f"ESCALATION: {reason} ({failure_class})")

        updates: dict[str, Any] = {
            "pending_escalation": {
                "signal": "NEED_INTERVENTION",
                "node_id": "orchestrator",
                "orchestrator_summary": reason,
                "error_detail": {"failure_class": failure_class, "message": reason}
            },
            "current_output": {
                "signal": "NEED_INTERVENTION",
                "node_id": "orchestrator",
                "orchestrator_summary": reason,
                "error_detail": {"failure_class": failure_class, "message": reason}
            }
        }

        # Dead-end cascading (F-REQ-34 / Appendix §1.2)
        # If we are escalating because of a node failure, find stalled nodes
        # that depend on that node's result and mark them as DEAD_END.
        current_output = state.get("current_output", {})
        failed_node_id = current_output.get("node_id")
        if failed_node_id and current_output.get("signal") in [Signal.FAILED, Signal.NEED_INTERVENTION]:
            stalled_queue = list(state.get("stalled_queue", []))

            new_stalled = []
            new_completed = []
            timeline = []

            for sid in stalled_queue:
                meta = self.bag_manager.manifest.nodes.get(sid)
                if meta and meta.requires:
                    # Key convention: dependency on node 'X' looks for 'X_result'
                    required_key = f"{failed_node_id}_result"
                    if required_key in meta.requires:
                        # Cascade!
                        self.signal_manager.mark_dead_end(sid)
                        new_completed.append(sid)
                        timeline.append({
                            "node_id": sid,
                            "signal": "DEAD_END",
                            "summary": f"Cascaded failure: prerequisite '{failed_node_id}' failed."
                        })
                    else:
                        new_stalled.append(sid)
                else:
                    new_stalled.append(sid)

            if new_completed:
                updates["stalled_queue"] = new_stalled
                updates["completed_nodes"] = new_completed
                updates["timeline"] = timeline

        return updates

    def suspend(self, state: dict[str, Any], args: dict[str, Any]) -> dict[str, Any]:
        """Suspends the workflow to ask the human a question."""
        msg = args.get("human_request_message", "Please review.")
        logger.info(f"SUSPEND: {msg}")
        return {
            "suspended": True,
            "current_output": {
                "signal": "HOLD_FOR_HUMAN",
                "node_id": "orchestrator",
                "human_request": {"message": msg}
            }
        }

    def complete(self, state: dict[str, Any], args: dict[str, Any]) -> dict[str, Any]:
        """Marks the workflow as successfully completed."""
        msg = args.get("final_summary", "Job complete.")
        logger.info(f"COMPLETE: {msg}")
        return {
            "current_output": {
                "signal": "DONE",
                "node_id": "orchestrator",
                "orchestrator_summary": msg
            }
        }

# Export the tools
__all__ = ["CompleteArgs", "DispatchNodeArgs", "EscalateArgs", "OrchestratorTools", "SuspendArgs"]
