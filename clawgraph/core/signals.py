"""SignalManager — transient telemetry and state tracking for ClawGraph.

The SignalManager maintains an in-memory snapshot of current node statuses
(the "Live Buffer") and handles output deduplication. It does NOT persist
state — that's the Session DB's job. On crash/resume, SignalManager state
is reset and nodes are marked STALE.

Architecture ref: 05_ARCHITECTURE.md §10
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum

from clawgraph.core.exceptions import SchemaVersionError
from clawgraph.core.models import ClawOutput, Signal

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

    def __init__(self) -> None:
        self._node_states: dict[str, NodeState] = {}
        self._seen_output_ids: set[str] = set()

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
            updated_at=datetime.now(),
        )

        logger.info(
            "Node '%s' → %s (signal=%s)",
            output.node_id,
            new_status.value,
            output.signal.value,
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

    def mark_stalled(self, node_id: str) -> None:
        """Mark a node as STALLED (prerequisites not met)."""
        state = self._node_states.get(node_id)
        if state is None:
            state = NodeState(node_id=node_id)
            self._node_states[node_id] = state
        state.status = NodeStatus.STALLED
        state.updated_at = datetime.now()

    def get_node_state(self, node_id: str) -> NodeState | None:
        """Get the current state of a specific node."""
        return self._node_states.get(node_id)

    def get_hud_snapshot(self) -> dict[str, dict[str, str | None]]:
        """Return the current state of all tracked nodes for HUD rendering.

        Returns a dict keyed by node_id with status, last_signal, and summary.
        This is the data source for get_hud_snapshot() in the external API.
        """
        return {
            node_id: {
                "status": state.status.value,
                "last_signal": state.last_signal.value if state.last_signal else None,
                "summary": state.last_summary,
                "updated_at": (
                    state.updated_at.isoformat() if state.updated_at else None
                ),
            }
            for node_id, state in self._node_states.items()
        }

    def reset(self) -> None:
        """Clear all transient state.

        Called on crash recovery. All nodes are effectively "unknown" until
        they emit new signals. The Session DB and LangGraph checkpointer
        hold the durable history.
        """
        self._node_states.clear()
        self._seen_output_ids.clear()
        logger.info("SignalManager reset — all transient state cleared.")

    @property
    def node_count(self) -> int:
        """Number of nodes currently being tracked."""
        return len(self._node_states)

    @property
    def active_nodes(self) -> list[str]:
        """Node IDs currently in RUNNING status."""
        return [
            nid
            for nid, state in self._node_states.items()
            if state.status == NodeStatus.RUNNING
        ]
