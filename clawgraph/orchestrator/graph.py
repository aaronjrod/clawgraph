"""ClawBag — the developer-facing entry point for ClawGraph workflows.

ClawBag wraps BagManager + SignalManager + LangGraph StateGraph into a
single cohesive unit. It handles graph compilation, lazy recompilation,
job lifecycle (start/resume), and HITL handler registration.

Architecture ref: 05_ARCHITECTURE.md S2-4, S8
"""

from __future__ import annotations

import logging
import operator
from collections.abc import Callable
from datetime import datetime
from typing import Any, TypedDict, Annotated

from clawgraph.bag.manager import BagManager
from clawgraph.bag.skills import SkillsContextManager
from clawgraph.core.models import ArchiveEntry, BagContract
from clawgraph.core.signals import SignalManager
from clawgraph.core.timeline import TimelineBuffer
from clawgraph.orchestrator.prompts import build_orchestrator_prompt

logger = logging.getLogger(__name__)


# ── LangGraph State Schema ────────────────────────────────────────────────────


class BagState(TypedDict, total=False):
    """The shared state schema for a ClawGraph bag's LangGraph topology.

    This is the TypedDict that flows through the StateGraph. Keys follow
    the pointer-based state philosophy — documents are referenced by URI,
    never inlined.

    Ref: 05_ARCHITECTURE.md §5
    """

    # ── Mission ────────────────────────────────────────────────────
    objective: str  # High-level goal from the Super-Orchestrator.
    thread_id: str  # LangGraph thread identifier for checkpointing.

    # ── Bag Context ────────────────────────────────────────────────
    bag_manifest: dict[str, Any]  # Tier 1 manifest snapshot (from get_inventory).
    bag_name: str  # Name of this bag (for domain visibility).
    document_archive: dict[str, Any]  # {artifact_id: ArchiveEntry|str} -- pointer registry.
    phase_history: Annotated[list[str], operator.add]  # Sequential accomplishment summaries.

    # ── Execution Queues (Gap 6 / F-REQ-12) ───────────────────────
    current_output: dict[str, Any]  # Serialized ClawOutput from last node.
    current_node_id: str | None  # Node being dispatched (or None if idle).
    max_iterations: int  # Budget for Orchestrator reasoning loops.
    iteration_count: int  # How many dispatches have occurred.
    ready_queue: list[str]  # Nodes whose prereqs are satisfied.
    stalled_queue: list[str]  # Nodes waiting on prerequisites.
    completed_nodes: Annotated[list[str], operator.add]  # Nodes that have finished (DONE).

    # ── Orchestrator ───────────────────────────────────────────────
    orchestrator_prompt: str  # The assembled system prompt.
    pending_escalation: dict[str, Any] | None  # Escalation payload for SO.

    # ── Escalation Policy Tracking (Gap 3 / F-REQ-10) ─────────────
    need_info_tracking: dict[str, Any]  # {node_id: {retries, first_seen}}

    # ── Timeline Events (in-state log for observability) ──────────
    timeline: Annotated[list[dict[str, Any]], operator.add]  # Serialized event dicts.

    # ── HITL ───────────────────────────────────────────────────────
    human_response: str | None  # Injected by resume_job().
    suspended: bool  # True when waiting for human input.


def _entry_visible(entry: Any, bag_name: str) -> bool:
    """Check if a document_archive entry is visible to the given bag.

    Visibility rule (F-REQ-17):
    - Plain strings (legacy) are always visible.
    - ArchiveEntry dicts: visible if ``domain == bag_name`` or ``"public" in tags``.
    - None (missing key) → not visible.
    """
    if entry is None:
        return False
    if isinstance(entry, str):
        return True  # Legacy format — always visible.
    if isinstance(entry, dict):
        domain = entry.get("domain", "")
        tags = entry.get("tags", [])
        return domain == bag_name or "public" in tags
    return False


# ── ClawBag ───────────────────────────────────────────────────────────────────


class ClawBag:
    """The developer-facing entry point for a ClawGraph workflow.

    A ClawBag is a self-contained workspace: it owns a BagManager (nodes),
    a SignalManager (telemetry), and a compiled LangGraph StateGraph
    (execution engine). The Super-Orchestrator interacts with the bag
    through its public API.

    Usage:
        bag = ClawBag(name="research_ops")
        bag.manager.register_node(summarize_doc)
        bag.manager.register_node(verify_output)
        result = bag.start_job(
            objective="Summarize and verify the research document.",
            inputs={"target_doc": "s3://docs/paper.pdf"},
            max_iterations=5,
        )
    """

    def __init__(
        self,
        name: str,
        max_iterations: int = 10,
        skills_dir: str | None = None,
        checkpointer: Any | None = None,
        contract: BagContract | None = None,
    ) -> None:
        self._name = name
        self._max_iterations = max_iterations

        # Core components.
        self._manager = BagManager(name=name)
        self._timeline = TimelineBuffer()
        self._signal_manager = SignalManager(timeline_buffer=self._timeline)
        self._skills = SkillsContextManager(skills_dir=skills_dir)

        # Compilation state.
        self._compiled_graph: Any | None = None
        self._last_compiled_version: int = -1

        # Durable checkpointer (Architecture §8).
        self._checkpointer = checkpointer

        # Bag contract (F-REQ-25).
        self._contract = contract

        # HITL handler.
        self._hitl_handler: Callable[..., Any] | None = None

    # ── Properties ─────────────────────────────────────────────────

    @property
    def name(self) -> str:
        return self._name

    @property
    def contract(self) -> BagContract | None:
        """Access the BagContract (F-REQ-25)."""
        return self._contract

    @property
    def manager(self) -> BagManager:
        """Access the BagManager for node CRUD."""
        return self._manager

    @property
    def signal_manager(self) -> SignalManager:
        """Access the SignalManager for telemetry."""
        return self._signal_manager

    @property
    def skills(self) -> SkillsContextManager:
        """Access the SkillsContextManager."""
        return self._skills

    @property
    def is_compiled(self) -> bool:
        """Whether the graph has been compiled at least once."""
        return self._compiled_graph is not None

    @property
    def is_dirty(self) -> bool:
        """Whether the manifest has changed since last compilation."""
        return self._manager.version != self._last_compiled_version

    # ── HITL Handler ──────────────────────────────────────────────

    def register_hitl_handler(self, handler: Callable[..., Any]) -> None:
        """Register a delivery mechanism for HOLD_FOR_HUMAN signals.

        The handler is called with (thread_id: str, human_request: dict)
        when a node emits HOLD_FOR_HUMAN. The handler is responsible for
        delivering the request to the user (Slack, email, WebSocket, etc.).

        Ref: 05_ARCHITECTURE.md §8.1
        """
        self._hitl_handler = handler
        logger.info("HITL handler registered for bag '%s'.", self._name)

    # ── Graph Compilation ─────────────────────────────────────────

    def compile_graph(self) -> Any:
        """Build the LangGraph StateGraph from the current manifest.

        This creates a hub-and-spoke topology:
        - The Orchestrator is the central node.
        - Each registered ClawNode is a spoke.
        - Conditional edges route signals back to the Orchestrator.

        Returns:
            The compiled LangGraph graph.
        """
        from clawgraph.orchestrator.hub import build_hub_graph

        graph = build_hub_graph(
            bag_manager=self._manager,
            signal_manager=self._signal_manager,
            hitl_handler=self._hitl_handler,
            timeline_buffer=self._signal_manager._timeline,
            checkpointer=self._checkpointer,
            contract=self._contract,
        )

        self._compiled_graph = graph
        self._last_compiled_version = self._manager.version

        logger.info(
            "Compiled graph for bag '%s' at manifest v%d (%d nodes).",
            self._name,
            self._manager.version,
            len(self._manager),
        )
        return graph

    def compile_graph_if_dirty(self) -> Any:
        """Recompile the graph only if the manifest has changed.

        This is the "lazy compilation" strategy from Architecture §8.
        It prevents unnecessary recompilation on every job start when
        the bag hasn't changed.

        Returns:
            The compiled LangGraph graph (fresh or cached).
        """
        if self.is_dirty or not self.is_compiled:
            logger.info(
                "Manifest dirty (v%d vs compiled v%d). Recompiling.",
                self._manager.version,
                self._last_compiled_version,
            )
            return self.compile_graph()

        logger.debug("Manifest clean (v%d). Using cached graph.", self._manager.version)
        return self._compiled_graph

    # ── Job Lifecycle ─────────────────────────────────────────────

    def start_job(
        self,
        objective: str,
        inputs: dict[str, str] | None = None,
        max_iterations: int | None = None,
        thread_id: str | None = None,
    ) -> BagState:
        """Start a new job on this bag.

        1. Compiles the graph if dirty (lazy compilation).
        2. Locks the manifest to prevent mid-execution mutation.
        3. Builds the initial BagState.
        4. Invokes the compiled graph.
        5. Unlocks the manifest on completion.

        Args:
            objective: The high-level goal for this job.
            inputs: Initial document_archive entries {artifact_id: uri}.
            max_iterations: Override the default iteration budget.
            thread_id: LangGraph thread ID for checkpointing.

        Returns:
            The final BagState after execution completes or suspends.
        """
        # Validate BagContract inputs (F-REQ-25).
        if self._contract and self._contract.required_inputs:
            raw = inputs or {}
            missing = [r for r in self._contract.required_inputs if r not in raw]
            if missing:
                from clawgraph.core.exceptions import BagContractError

                raise BagContractError(f"Missing required inputs: {missing}")

        # Compile if needed.
        self.compile_graph_if_dirty()

        # Reset telemetry for fresh job.
        self._signal_manager.reset()

        # Lock manifest during execution.
        self._manager.lock()

        iterations = max_iterations or self._max_iterations

        # Build initial state.
        raw_inputs = inputs or {}
        inventory = self._manager.get_inventory()

        # Convert raw string inputs to ArchiveEntry objects.
        archive: dict[str, Any] = {}
        for key, val in raw_inputs.items():
            if isinstance(val, str):
                archive[key] = ArchiveEntry(
                    uri=val,
                    domain=self._name,
                    tags=["public"],
                    created_by="input",
                ).model_dump()
            else:
                archive[key] = val  # Already an ArchiveEntry dict.

        # Partition nodes into ready vs stalled based on prereqs.
        ready: list[str] = []
        stalled: list[str] = []
        initial_timeline: list[dict[str, Any]] = []
        for nid, meta in inventory.get("nodes", {}).items():
            requires = meta.get("requires") or []
            missing = [r for r in requires if not _entry_visible(archive.get(r), self._name)]
            if missing:
                stalled.append(nid)
                initial_timeline.append(
                    {
                        "node_id": nid,
                        "signal": "STALLED",
                        "summary": f"Missing: {missing}",
                    }
                )
            else:
                ready.append(nid)

        state: BagState = {
            "objective": objective,
            "thread_id": thread_id or f"{self._name}_{datetime.now().isoformat()}",
            "bag_manifest": inventory,
            "document_archive": archive,
            "bag_name": self._name,
            "phase_history": [],
            "current_output": {},
            "current_node_id": None,
            "max_iterations": iterations,
            "iteration_count": 0,
            "ready_queue": ready,
            "stalled_queue": stalled,
            "completed_nodes": [],
            "orchestrator_prompt": build_orchestrator_prompt(
                bag_name=self._name,
                max_iterations=iterations,
            ),
            "pending_escalation": None,
            "need_info_tracking": {},
            "timeline": initial_timeline,
            "human_response": None,
            "suspended": False,
        }

        try:
            logger.info(
                "Starting job on bag '%s': objective='%s', budget=%d iterations.",
                self._name,
                objective[:80],
                iterations,
            )

            # Wire thread_id for timeline event association.
            self._signal_manager.set_active_thread(state["thread_id"])

            # Execute the graph.
            # NOTE: In Phase 5, this will use the LangGraph checkpointer
            # for durable persistence. For now, we do a synchronous run.
            if self._compiled_graph is not None:
                result = self._compiled_graph.invoke(state)
                return result  # type: ignore[no-any-return]

            logger.warning("No compiled graph — returning initial state.")
            return state

        finally:
            self._manager.unlock()

    def resume_job(
        self,
        thread_id: str,
        human_response: str,
    ) -> BagState:
        """Resume a suspended job after human input.

        Rehydrates the checkpoint, injects the human response, and
        continues execution. Recompiles the graph if the manifest changed
        during suspension.

        Args:
            thread_id: The thread_id of the suspended job.
            human_response: The human's response to the HOLD_FOR_HUMAN request.

        Returns:
            The final BagState after execution completes or re-suspends.

        Ref: 05_ARCHITECTURE.md §8.1
        """
        # Recompile if the SO modified the bag during suspension.
        self.compile_graph_if_dirty()

        self._manager.lock()

        try:
            logger.info(
                "Resuming job '%s' on bag '%s' with human response.",
                thread_id,
                self._name,
            )

            # NOTE: In Phase 5, this will pull the checkpoint from the
            # Session DB and inject the response. For now, we build a
            # minimal state that signals resumption.
            state: BagState = {
                "objective": "",  # Will be restored from checkpoint.
                "thread_id": thread_id,
                "bag_manifest": self._manager.get_inventory(),
                "bag_name": self._name,
                "document_archive": {},
                "phase_history": [],
                "current_output": {},
                "current_node_id": None,
                "max_iterations": self._max_iterations,
                "iteration_count": 0,
                "ready_queue": [],
                "stalled_queue": [],
                "completed_nodes": [],
                "orchestrator_prompt": build_orchestrator_prompt(
                    bag_name=self._name,
                    max_iterations=self._max_iterations,
                ),
                "pending_escalation": None,
                "need_info_tracking": {},
                "timeline": [],
                "human_response": human_response,
                "suspended": False,
            }

            if self._compiled_graph is not None:
                result = self._compiled_graph.invoke(state)
                return result  # type: ignore[no-any-return]

            return state

        finally:
            self._manager.unlock()

    # ── Convenience ────────────────────────────────────────────────

    def get_hud_snapshot(self, thread_id: str = "") -> dict[str, Any]:
        """Return the merged HUD snapshot (Part 7.1 shape)."""
        inventory = self._manager.get_inventory()
        return self._signal_manager.get_hud_snapshot(
            thread_id=thread_id,
            manifest_nodes=inventory.get("nodes"),
        )

    def audit_node(self, node_id: str) -> dict[str, Any]:
        """Return Tier 2 source + Tier 1 metadata for a node.

        Delegates to BagManager.audit_node(). (F-REQ-19)
        """
        return self._manager.audit_node(node_id)

    def rollback_bag(self, version: int) -> None:
        """Revert the bag manifest to a prior version.

        Delegates to BagManager.rollback_bag(), resets signal state,
        and marks the graph as dirty for recompilation. (Architecture S11)
        """
        self._manager.rollback_bag(version)
        self._signal_manager.reset()
        # Graph is now dirty (version mismatch triggers recompilation).

    def get_summary(self, thread_id: str) -> str:
        """Return the accumulated phase summaries for a job. (FRS S3.2)

        Extracts the phase_history from the TimelineBuffer if available,
        falling back to a summary of node states from the SignalManager.

        Args:
            thread_id: The job thread ID.

        Returns:
            A newline-separated string of accomplishment summaries.
        """
        # If we have a TimelineBuffer, use it for the durable record.
        if self._signal_manager._timeline:
            events = self._signal_manager._timeline.get_timeline(thread_id)
            summaries = [
                f"[{e.signal.value if e.signal else 'EVENT'}] {e.node_id}: {e.summary}"
                for e in events
                if e.summary
            ]
            return "\n".join(summaries)

        # Fallback: generate from SignalManager state.
        snapshot = self._signal_manager.get_hud_snapshot(thread_id=thread_id)
        summaries = [
            f"[{n['signal'] or 'PENDING'}] {n['id']}: {n['summary'] or 'No summary'}"
            for n in snapshot.get("nodes", [])
        ]
        return "\n".join(summaries)

    def inject_info(
        self,
        thread_id: str,
        node_id: str,
        answer: Any,
    ) -> BagState:
        """Inject an answer for a NEED_INFO node. (Appendix §1.7)

        Writes the answer into ``continuation_context`` and re-enqueues
        the node into ``ready_queue`` so it can be re-dispatched.

        Args:
            thread_id: The job thread ID.
            node_id: The node that asked the question.
            answer: The answer payload (dict, str, etc.).

        Returns:
            The updated BagState snapshot.
        """
        # Build a synthetic state update.
        state: BagState = {  # type: ignore[typeddict-unknown-key]
            "continuation_context": {node_id: answer},
            "ready_queue": [node_id],
        }
        logger.info(
            "inject_info: answer injected for '%s' on thread '%s'.",
            node_id,
            thread_id,
        )
        return state

    def inspect_event(
        self,
        thread_id: str,
        node_id: str,
    ) -> dict[str, Any] | None:
        """Inspect a node's latest timeline event + archive entry. (F-REQ-33)

        Retrieves the most recent timeline event for ``node_id`` and
        enriches it with the corresponding ``ArchiveEntry`` from the
        ``document_archive`` if a ``result_uri`` exists.

        Args:
            thread_id: The job thread ID.
            node_id: The node to inspect.

        Returns:
            Dict with event fields + 'archive_entry', or None if not found.
        """
        if not self._signal_manager._timeline:
            return None

        events = self._signal_manager._timeline.get_timeline(thread_id)
        # Find the latest event for this node.
        node_events = [e for e in events if e.node_id == node_id]
        if not node_events:
            return None

        latest = node_events[-1]
        result: dict[str, Any] = {
            "node_id": latest.node_id,
            "signal": latest.signal.value if latest.signal else None,
            "summary": latest.summary,
        }

        # Enrich with archive entry if available.
        node_state = self._signal_manager.get_node_state(node_id)
        if node_state and node_state.result_uri:
            # Look for the archive entry in the last known state.
            result["archive_entry"] = {
                "uri": node_state.result_uri,
                "node_id": node_id,
            }
        else:
            result["archive_entry"] = None

        return result

    def __repr__(self) -> str:
        status = "compiled" if self.is_compiled else "uncompiled"
        dirty = " (dirty)" if self.is_dirty else ""
        return (
            f"ClawBag(name='{self._name}', "
            f"nodes={len(self._manager)}, "
            f"v{self._manager.version}, "
            f"{status}{dirty})"
        )
