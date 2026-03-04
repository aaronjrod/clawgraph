"""TimelineEvent and TimelineBuffer -- durable event log for ClawGraph.

The Timeline provides a structured log of lifecycle events emitted during
job execution. In Phase 4 this lives in memory; Phase 5 will persist to
Sqlite/Postgres.

Architecture ref: 05_ARCHITECTURE.md S10.6, FRS F-REQ-30/31
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any
from uuid import uuid4

from clawgraph.core.models import ClawOutput, Signal

logger = logging.getLogger(__name__)


@dataclass
class TimelineEvent:
    """A single lifecycle event in the durable timeline. (F-REQ-31)

    Schema: {event_id, timestamp, thread_id, node_id, signal,
             summary, duration_ms, tier, metadata}
    """

    event_id: str = field(default_factory=lambda: str(uuid4()))
    timestamp: datetime = field(default_factory=datetime.now)
    thread_id: str = ""
    node_id: str = ""
    signal: Signal | None = None
    summary: str = ""
    duration_ms: float | None = None
    tier: int = 1  # 1=routing, 2=detail, 3=raw
    metadata: dict[str, Any] = field(default_factory=dict)


class TimelineBuffer:
    """In-memory event log for a single thread. (F-REQ-30)

    Captures every signal transition as a TimelineEvent. Phase 5 will
    add a persistence backend (Sqlite/Postgres) via fire-and-forget
    emission.

    Usage:
        buf = TimelineBuffer()
        buf.record_signal(thread_id, output)
        events = buf.get_timeline(thread_id)
    """

    def __init__(self) -> None:
        self._events: dict[str, list[TimelineEvent]] = {}

    def record_signal(
        self,
        thread_id: str,
        output: ClawOutput,
        duration_ms: float | None = None,
    ) -> TimelineEvent:
        """Record a ClawOutput as a timeline event.

        Args:
            thread_id: The job thread ID.
            output: The ClawOutput to record.
            duration_ms: Optional execution duration.

        Returns:
            The created TimelineEvent.
        """
        event = TimelineEvent(
            thread_id=thread_id,
            node_id=output.node_id,
            signal=output.signal,
            summary=output.orchestrator_summary,
            duration_ms=duration_ms,
            tier=1,
            metadata={
                "output_id": output.output_id,
                "result_uri": output.result_uri,
                "orchestrator_synthesized": output.orchestrator_synthesized,
            },
        )

        if thread_id not in self._events:
            self._events[thread_id] = []
        self._events[thread_id].append(event)

        logger.debug(
            "Timeline: %s [%s] %s -> %s",
            thread_id,
            output.node_id,
            output.signal.value,
            output.orchestrator_summary[:60],
        )

        return event

    def record_orchestrator_event(
        self,
        thread_id: str,
        node_id: str,
        status: str,
        summary: str,
    ) -> TimelineEvent:
        """Record an Orchestrator-level event (RUNNING, STALLED, RESOLVING).

        These are NOT node signals — they're observability events from
        the Orchestrator itself.
        """
        event = TimelineEvent(
            thread_id=thread_id,
            node_id=node_id,
            signal=None,
            summary=summary,
            tier=2,
            metadata={"orchestrator_status": status},
        )

        if thread_id not in self._events:
            self._events[thread_id] = []
        self._events[thread_id].append(event)

        return event

    def get_timeline(
        self,
        thread_id: str,
        limit: int | None = None,
    ) -> list[TimelineEvent]:
        """Retrieve the event timeline for a thread. (F-REQ-30)

        Args:
            thread_id: The thread to query.
            limit: Max events to return (most recent). None = all.

        Returns:
            List of TimelineEvents in chronological order.
        """
        events = self._events.get(thread_id, [])
        if limit is not None:
            return events[-limit:]
        return list(events)

    def get_hitl_context(
        self,
        thread_id: str,
        n: int = 5,
    ) -> list[TimelineEvent]:
        """Get the N most recent events for HITL context. (F-REQ-32)

        When a HOLD_FOR_HUMAN signal is emitted, this provides the
        preceding events as lead-up context for the human reviewer.
        """
        return self.get_timeline(thread_id, limit=n)

    def event_count(self, thread_id: str) -> int:
        """Number of events recorded for a thread."""
        return len(self._events.get(thread_id, []))

    def clear(self, thread_id: str | None = None) -> None:
        """Clear events. If thread_id is None, clear all."""
        if thread_id:
            self._events.pop(thread_id, None)
        else:
            self._events.clear()

    def __repr__(self) -> str:
        total = sum(len(v) for v in self._events.values())
        return f"TimelineBuffer(threads={len(self._events)}, events={total})"
