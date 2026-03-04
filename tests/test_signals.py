"""Tests for clawgraph.core.signals — SignalManager state tracking."""

import pytest

from clawgraph.core.exceptions import SchemaVersionError
from clawgraph.core.models import (
    ClawOutput,
    ErrorDetail,
    FailureClass,
    Signal,
)
from clawgraph.core.signals import NodeStatus, SignalManager


def _make_output(
    signal: Signal = Signal.DONE,
    node_id: str = "test_node",
    **kwargs,
) -> ClawOutput:
    """Helper to construct valid ClawOutputs for testing."""
    defaults = {
        "orchestrator_summary": f"Node {node_id} signal: {signal.value}",
    }
    # Provide signal-required fields.
    if signal in (Signal.DONE, Signal.PARTIAL):
        defaults["result_uri"] = kwargs.pop("result_uri", "uri://test")
    if signal in (Signal.FAILED, Signal.NEED_INTERVENTION):
        defaults["error_detail"] = kwargs.pop(
            "error_detail",
            ErrorDetail(failure_class=FailureClass.LOGIC_ERROR, message="test error"),
        )
    if signal == Signal.NEED_INFO:
        from clawgraph.core.models import InfoRequest
        defaults["info_request"] = kwargs.pop(
            "info_request",
            InfoRequest(question="test?", context="test context"),
        )
    if signal == Signal.HOLD_FOR_HUMAN:
        from clawgraph.core.models import HumanRequest
        defaults["human_request"] = kwargs.pop(
            "human_request",
            HumanRequest(message="Approve?"),
        )

    defaults.update(kwargs)
    return ClawOutput(signal=signal, node_id=node_id, **defaults)


class TestSignalManagerProcessing:
    def test_process_done(self):
        sm = SignalManager()
        output = _make_output(Signal.DONE, "node_a")
        assert sm.process_signal(output) is True
        state = sm.get_node_state("node_a")
        assert state is not None
        assert state.status == NodeStatus.DONE
        assert state.last_signal == Signal.DONE

    def test_process_failed(self):
        sm = SignalManager()
        output = _make_output(Signal.FAILED, "node_b")
        assert sm.process_signal(output) is True
        assert sm.get_node_state("node_b").status == NodeStatus.FAILED

    def test_process_suspended_on_need_info(self):
        sm = SignalManager()
        output = _make_output(Signal.NEED_INFO, "node_c")
        sm.process_signal(output)
        assert sm.get_node_state("node_c").status == NodeStatus.SUSPENDED

    def test_process_suspended_on_hold_for_human(self):
        sm = SignalManager()
        output = _make_output(Signal.HOLD_FOR_HUMAN, "node_d")
        sm.process_signal(output)
        assert sm.get_node_state("node_d").status == NodeStatus.SUSPENDED

    def test_process_partial(self):
        sm = SignalManager()
        output = _make_output(Signal.PARTIAL, "node_e")
        sm.process_signal(output)
        assert sm.get_node_state("node_e").status == NodeStatus.PARTIAL


class TestSignalManagerDedup:
    def test_duplicate_output_id_skipped(self):
        sm = SignalManager()
        output = _make_output(Signal.DONE, "node_a")
        assert sm.process_signal(output) is True
        # Same output again → should be skipped.
        assert sm.process_signal(output) is False

    def test_different_output_ids_both_processed(self):
        sm = SignalManager()
        out1 = _make_output(Signal.DONE, "node_a")
        out2 = _make_output(Signal.DONE, "node_a")  # Different UUID auto-generated.
        assert sm.process_signal(out1) is True
        assert sm.process_signal(out2) is True


class TestSignalManagerSchemaVersion:
    def test_future_version_raises(self):
        sm = SignalManager()
        output = _make_output(Signal.DONE, "node_a", schema_version=999)
        with pytest.raises(SchemaVersionError) as exc_info:
            sm.process_signal(output)
        assert exc_info.value.received == 999
        assert exc_info.value.current == 1

    def test_older_version_logs_warning(self, caplog):
        sm = SignalManager()
        output = _make_output(Signal.DONE, "node_a", schema_version=0)
        with caplog.at_level("WARNING"):
            result = sm.process_signal(output)
        assert result is True  # Still processed.
        assert "schema v0" in caplog.text


class TestSignalManagerHUD:
    def test_hud_snapshot_empty(self):
        sm = SignalManager()
        snapshot = sm.get_hud_snapshot()
        assert snapshot == {}

    def test_hud_snapshot_after_signals(self):
        sm = SignalManager()
        sm.process_signal(_make_output(Signal.DONE, "node_a"))
        sm.process_signal(_make_output(Signal.FAILED, "node_b"))
        snapshot = sm.get_hud_snapshot()
        assert "node_a" in snapshot
        assert "node_b" in snapshot
        assert snapshot["node_a"]["status"] == "DONE"
        assert snapshot["node_b"]["status"] == "FAILED"

    def test_mark_running(self):
        sm = SignalManager()
        sm.mark_running("node_x")
        assert sm.get_node_state("node_x").status == NodeStatus.RUNNING
        assert "node_x" in sm.active_nodes

    def test_mark_stalled(self):
        sm = SignalManager()
        sm.mark_stalled("node_y")
        assert sm.get_node_state("node_y").status == NodeStatus.STALLED


class TestSignalManagerReset:
    def test_reset_clears_all(self):
        sm = SignalManager()
        sm.process_signal(_make_output(Signal.DONE, "node_a"))
        sm.process_signal(_make_output(Signal.FAILED, "node_b"))
        assert sm.node_count == 2

        sm.reset()
        assert sm.node_count == 0
        assert sm.get_hud_snapshot() == {}

    def test_reset_allows_reprocessing_same_output_id(self):
        sm = SignalManager()
        output = _make_output(Signal.DONE, "node_a")
        sm.process_signal(output)
        sm.reset()
        # After reset, same output_id should be accepted again.
        assert sm.process_signal(output) is True
