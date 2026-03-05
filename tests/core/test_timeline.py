"""Tests for clawgraph.core.timeline -- TimelineBuffer and TimelineEvent."""

from clawgraph.core.models import ClawOutput, ErrorDetail, FailureClass, Signal
from clawgraph.core.timeline import TimelineBuffer, TimelineEvent


def _done_output(node_id: str) -> ClawOutput:
    return ClawOutput(
        signal=Signal.DONE,
        node_id=node_id,
        orchestrator_summary=f"{node_id} completed.",
        result_uri=f"uri://{node_id}.json",
    )


def _failed_output(node_id: str) -> ClawOutput:
    return ClawOutput(
        signal=Signal.FAILED,
        node_id=node_id,
        orchestrator_summary=f"{node_id} failed.",
        error_detail=ErrorDetail(
            failure_class=FailureClass.LOGIC_ERROR,
            message="test failure",
        ),
    )


class TestTimelineEvent:
    def test_defaults(self):
        event = TimelineEvent()
        assert event.event_id  # UUID generated
        assert event.timestamp is not None
        assert event.tier == 1

    def test_custom_fields(self):
        event = TimelineEvent(
            thread_id="t1",
            node_id="node_a",
            signal=Signal.DONE,
            summary="Done.",
        )
        assert event.thread_id == "t1"
        assert event.node_id == "node_a"
        assert event.signal == Signal.DONE


class TestTimelineBufferRecording:
    def test_record_signal(self):
        buf = TimelineBuffer()
        output = _done_output("node_a")
        event = buf.record_signal("thread_1", output)
        assert event.thread_id == "thread_1"
        assert event.node_id == "node_a"
        assert event.signal == Signal.DONE
        assert event.summary == "node_a completed."
        assert event.metadata["result_uri"] == "uri://node_a.json"

    def test_record_multiple_signals(self):
        buf = TimelineBuffer()
        buf.record_signal("t1", _done_output("a"))
        buf.record_signal("t1", _failed_output("b"))
        assert buf.event_count("t1") == 2

    def test_record_orchestrator_event(self):
        buf = TimelineBuffer()
        event = buf.record_orchestrator_event(
            thread_id="t1",
            node_id="node_x",
            status="RUNNING",
            summary="Starting node_x.",
        )
        assert event.tier == 2
        assert event.metadata["orchestrator_status"] == "RUNNING"

    def test_separate_threads(self):
        buf = TimelineBuffer()
        buf.record_signal("t1", _done_output("a"))
        buf.record_signal("t2", _done_output("b"))
        assert buf.event_count("t1") == 1
        assert buf.event_count("t2") == 1


class TestTimelineBufferRetrieval:
    def test_get_timeline(self):
        buf = TimelineBuffer()
        buf.record_signal("t1", _done_output("a"))
        buf.record_signal("t1", _done_output("b"))
        events = buf.get_timeline("t1")
        assert len(events) == 2
        assert events[0].node_id == "a"
        assert events[1].node_id == "b"

    def test_get_timeline_with_limit(self):
        buf = TimelineBuffer()
        for i in range(10):
            buf.record_signal("t1", _done_output(f"node_{i}"))
        events = buf.get_timeline("t1", limit=3)
        assert len(events) == 3
        # Should be the 3 most recent.
        assert events[0].node_id == "node_7"

    def test_get_timeline_empty_thread(self):
        buf = TimelineBuffer()
        assert buf.get_timeline("nonexistent") == []

    def test_get_hitl_context(self):
        buf = TimelineBuffer()
        for i in range(10):
            buf.record_signal("t1", _done_output(f"node_{i}"))
        context = buf.get_hitl_context("t1", n=3)
        assert len(context) == 3


class TestTimelineBufferManagement:
    def test_clear_single_thread(self):
        buf = TimelineBuffer()
        buf.record_signal("t1", _done_output("a"))
        buf.record_signal("t2", _done_output("b"))
        buf.clear("t1")
        assert buf.event_count("t1") == 0
        assert buf.event_count("t2") == 1

    def test_clear_all(self):
        buf = TimelineBuffer()
        buf.record_signal("t1", _done_output("a"))
        buf.record_signal("t2", _done_output("b"))
        buf.clear()
        assert buf.event_count("t1") == 0
        assert buf.event_count("t2") == 0

    def test_repr(self):
        buf = TimelineBuffer()
        buf.record_signal("t1", _done_output("a"))
        r = repr(buf)
        assert "threads=1" in r
        assert "events=1" in r
