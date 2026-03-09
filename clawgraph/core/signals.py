"""SignalManager — transient telemetry and state tracking for ClawGraph.

The SignalManager maintains an in-memory snapshot of current node statuses
(the "Live Buffer") and handles output deduplication. It does NOT persist
state — that's the Session DB's job. On crash/resume, SignalManager state
is reset and nodes are marked STALE.

Architecture ref: 05_ARCHITECTURE.md S10
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from typing import Any

from clawgraph.core.exceptions import SchemaVersionError
from clawgraph.core.models import ClawOutput, Signal
from clawgraph.core.timeline import TimelineBuffer

logger = logging.getLogger(__name__)

# Current schema version this SignalManager understands.
CURRENT_SCHEMA_VERSION = 1


class NodeStatus(StrEnum):
    """Internal status tracked by the SignalManager (NOT a node output signal)."""

    PENDING = "PENDING"
    RUNNING = "RUNNING"
    DONE = "DONE"
    FAILED = "FAILED"
    PARTIAL = "PARTIAL"
    STALLED = "STALLED"
    SUSPENDED = "SUSPENDED"  # NEED_INFO or HOLD_FOR_HUMAN
    STALE = "STALE"  # After crash/reset
    DEAD_END = "DEAD_END"  # Prerequisite failure (cascaded)


# Map from output Signal → internal NodeStatus
_SIGNAL_TO_STATUS: dict[Signal, NodeStatus] = {
    Signal.DONE: NodeStatus.DONE,
    Signal.FAILED: NodeStatus.FAILED,
    Signal.PARTIAL: NodeStatus.PARTIAL,
    Signal.NEED_INFO: NodeStatus.SUSPENDED,
    Signal.HOLD_FOR_HUMAN: NodeStatus.SUSPENDED,
    Signal.NEED_INTERVENTION: NodeStatus.FAILED,
}


@dataclass
class NodeState:
    """Snapshot of a single node's current state in the live buffer."""

    node_id: str
    status: NodeStatus = NodeStatus.PENDING
    last_signal: Signal | None = None
    last_summary: str | None = None
    last_output_id: str | None = None
    result_uri: str | None = None
    updated_at: datetime | None = None


class SignalManager:
    """In-memory telemetry hub for live node status tracking.

    Responsibilities:
        1. Track node states (the "HUD" source of truth)
        2. Deduplicate outputs by output_id (LangGraph replay safety)
        3. Validate schema_version compatibility
        4. Provide get_hud_snapshot() for visualization

    NOT responsible for:
        - Durable persistence (that's the Session DB)
        - Timeline event transformation (Phase 4)
        - Orchestrator routing decisions
    """

    def __init__(
        self,
        timeline_buffer: TimelineBuffer | None = None,
    ) -> None:
        self._node_states: dict[str, NodeState] = {}
        self._seen_output_ids: set[str] = set()
        self._result_uris: dict[str, str] = {}  # node_id -> result_uri (for linkage)
        self._timeline: TimelineBuffer | None = timeline_buffer
        self._active_thread_id: str | None = None
        self._chat_history: list[dict[str, Any]] = []

    def set_active_thread(self, thread_id: str | None) -> None:
        """Set the active job thread for timeline event association."""
        self._active_thread_id = thread_id

    def record_chat(self, sender: str, text: str) -> None:
        """Record an external chat message (e.g. from HUD) into the bag context."""
        entry = {
            "sender": sender,
            "text": text,
            "timestamp": datetime.now().isoformat()
        }
        self._chat_history.append(entry)
        logger.info("Chat recorded in SignalManager: [%s] %s", sender, text)

    def record_input_artifact(self, artifact_id: str, uri: str) -> None:
        """Record an initial input artifact for HUD visibility."""
        self._result_uris[artifact_id] = uri
        logger.info("Input artifact recorded in SignalManager: %s -> %s", artifact_id, uri)

    def process_signal(self, output: ClawOutput) -> bool:
        """Process a ClawOutput and update internal state.

        Args:
            output: The ClawOutput to process.

        Returns:
            True if the output was processed (new).
            False if it was a duplicate (already seen output_id).

        Raises:
            SchemaVersionError: If output.schema_version > CURRENT_SCHEMA_VERSION.
        """
        # ── Schema version check ──────────────────────────────────
        if output.schema_version > CURRENT_SCHEMA_VERSION:
            raise SchemaVersionError(
                received=output.schema_version,
                current=CURRENT_SCHEMA_VERSION,
            )
        if output.schema_version < CURRENT_SCHEMA_VERSION:
            logger.warning(
                "ClawOutput from node '%s' uses schema v%d (current: v%d). "
                "Processing with best-effort coercion.",
                output.node_id,
                output.schema_version,
                CURRENT_SCHEMA_VERSION,
            )

        # ── Deduplication ─────────────────────────────────────────
        if output.output_id in self._seen_output_ids:
            logger.debug(
                "Duplicate output_id '%s' from node '%s' — skipping.",
                output.output_id,
                output.node_id,
            )
            return False

        self._seen_output_ids.add(output.output_id)

        # ── State update ──────────────────────────────────────────
        new_status = _SIGNAL_TO_STATUS.get(output.signal, NodeStatus.FAILED)

        self._node_states[output.node_id] = NodeState(
            node_id=output.node_id,
            status=new_status,
            last_signal=output.signal,
            last_summary=output.orchestrator_summary,
            last_output_id=output.output_id,
            result_uri=output.result_uri,
            updated_at=datetime.now(),
        )

        # Track result_uri for implicit linkage.
        if output.result_uri:
            self._result_uris[output.node_id] = output.result_uri

        logger.info(
            "Node '%s' -> %s (signal=%s)",
            output.node_id,
            new_status.value,
            output.signal.value,
        )

        # Fire-and-forget: emit TimelineEvent to durable log. (Architecture S10.6)
        if self._timeline and self._active_thread_id:
            self._timeline.record_signal(
                thread_id=self._active_thread_id,
                output=output,
            )

        return True

    def mark_running(self, node_id: str) -> None:
        """Mark a node as RUNNING (Orchestrator status event, not a ClawOutput)."""
        state = self._node_states.get(node_id)
        if state is None:
            state = NodeState(node_id=node_id)
            self._node_states[node_id] = state
        state.status = NodeStatus.RUNNING
        state.updated_at = datetime.now()

        if self._timeline and self._active_thread_id:
            self._timeline.record_orchestrator_event(
                thread_id=self._active_thread_id,
                node_id=node_id,
                status="RUNNING",
                summary=f"Starting execution of {node_id}.",
            )

    def mark_stalled(self, node_id: str) -> None:
        """Mark a node as STALLED (prerequisites not met)."""
        state = self._node_states.get(node_id)
        if state is None:
            state = NodeState(node_id=node_id)
            self._node_states[node_id] = state
        state.status = NodeStatus.STALLED
        state.updated_at = datetime.now()

        if self._timeline and self._active_thread_id:
            self._timeline.record_orchestrator_event(
                thread_id=self._active_thread_id,
                node_id=node_id,
                status="STALLED",
                summary=f"{node_id} is waiting on prerequisites.",
            )

    def mark_dead_end(self, node_id: str) -> None:
        """Mark a node as DEAD_END (prerequisite failure)."""
        state = self._node_states.get(node_id)
        if state is None:
            state = NodeState(node_id=node_id)
            self._node_states[node_id] = state
        state.status = NodeStatus.DEAD_END
        state.updated_at = datetime.now()

        if self._timeline and self._active_thread_id:
            self._timeline.record_orchestrator_event(
                thread_id=self._active_thread_id,
                node_id=node_id,
                status="DEAD_END",
                summary=f"{node_id} cascaded to failure due to prerequisite failure.",
            )

    def get_node_state(self, node_id: str) -> NodeState | None:
        """Get the current state of a specific node."""
        return self._node_states.get(node_id)

    def get_hud_snapshot(
        self,
        thread_id: str = "",
        manifest_nodes: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Return the merged HUD snapshot (Part 7.1 JSON shape).

        Combines SignalManager live state with manifest topology to produce
        the full snapshot for Mission Control rendering.

        Args:
            thread_id: The current job thread ID.
            manifest_nodes: Manifest node metadata dict (from get_inventory).
                           If provided, includes nodes not yet tracked.

        Returns:
            Dict with 'thread_id', 'nodes', and 'links' arrays.
        """
        nodes: list[dict[str, Any]] = []
        links: list[dict[str, str]] = []

        # Collect all known node IDs.
        all_ids = set(self._node_states.keys())
        if manifest_nodes:
            all_ids |= set(manifest_nodes.keys())

        for node_id in sorted(all_ids):
            state = self._node_states.get(node_id)
            implicit = self._compute_implicit_links(node_id, manifest_nodes)

            node_entry: dict[str, Any] = {
                "id": node_id,
                "name": node_id,
                "status": state.status.value if state else NodeStatus.PENDING.value,
                "summary": state.last_summary if state else None,
                "signal": state.last_signal.value if state and state.last_signal else None,
                "result_uri": state.result_uri if state else None,
                "implicit_links": implicit,
            }
            nodes.append(node_entry)

            # Topology link: orchestrator -> node.
            links.append(
                {
                    "source": "orchestrator",
                    "target": node_id,
                    "type": "topology",
                }
            )

            # Data flow links from implicit linkage.
            for source_id in implicit:
                links.append(
                    {
                        "source": source_id,
                        "target": node_id,
                        "type": "data_flow",
                    }
                )

        return {
            "thread_id": thread_id,
            "nodes": nodes,
            "links": links,
        }

    def reset(self) -> None:
        """Clear all transient state.

        Called on crash recovery. All nodes are effectively "unknown" until
        they emit new signals. The Session DB and LangGraph checkpointer
        hold the durable history.
        """
        self._node_states.clear()
        self._seen_output_ids.clear()
        self._result_uris.clear()
        logger.info("SignalManager reset -- all transient state cleared.")

    @property
    def node_count(self) -> int:
        """Number of nodes currently being tracked."""
        return len(self._node_states)

    @property
    def active_nodes(self) -> list[str]:
        """Node IDs currently in RUNNING status."""
        return [
            nid for nid, state in self._node_states.items() if state.status == NodeStatus.RUNNING
        ]

    @property
    def overall_status(self) -> str:
        """Calculate the aggregate status of the bag based on its nodes' states."""
        if not self._node_states:
            return "IDLE"

        states = [n.status for n in self._node_states.values()]

        if NodeStatus.RUNNING in states:
            return NodeStatus.RUNNING.value
        if NodeStatus.SUSPENDED in states:
            return NodeStatus.SUSPENDED.value
        if NodeStatus.STALLED in states:
            return NodeStatus.STALLED.value
        if NodeStatus.FAILED in states:
            return NodeStatus.FAILED.value
        if NodeStatus.DONE in states:
            return NodeStatus.DONE.value

        return "IDLE"

    # -- Implicit Linkage Engine (Part 7.2) ---------------------------------

    def _compute_implicit_links(
        self,
        node_id: str,
        manifest_nodes: dict[str, Any] | None = None,
    ) -> list[str]:
        """Detect data-flow dependencies via URI matching.

        If node_id has 'requires' in its manifest metadata, check if
        any of those requirements match a result_uri produced by another node.
        """
        if not manifest_nodes or not self._result_uris:
            return []

        node_meta = manifest_nodes.get(node_id, {})
        requires = node_meta.get("requires", [])
        if not requires:
            return []

        # Check which producers have result_uris that could satisfy requirements.
        linked: list[str] = []
        for producer_id, _uri in self._result_uris.items():
            if producer_id == node_id:
                continue
            # Match if any requirement key appears in the producer's result_uri key.
            producer_key = f"{producer_id}_result"
            if producer_key in requires or producer_id in requires:
                linked.append(producer_id)

        return linked
