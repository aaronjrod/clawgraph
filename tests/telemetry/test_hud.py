"""TDD tests for telemetry HUD extraction (F-REQ-18, F-REQ-29)."""

from clawgraph.core.models import ClawOutput, Signal
from clawgraph.core.signals import SignalManager
from clawgraph.telemetry.hud import build_hud_snapshot


class TestBuildHudSnapshot:
    """Tests for the extracted build_hud_snapshot function."""

    def test_snapshot_shape(self):
        """Returned dict should have thread_id, nodes, links keys."""
        sm = SignalManager()
        snap = build_hud_snapshot(
            signal_manager=sm,
            thread_id="test-thread",
        )
        assert "thread_id" in snap
        assert "nodes" in snap
        assert "links" in snap
        assert snap["thread_id"] == "test-thread"

    def test_includes_node_status(self):
        """Each node entry should have status, last_signal, summary."""
        sm = SignalManager()
        output = ClawOutput(
            signal=Signal.DONE,
            node_id="worker_1",
            orchestrator_summary="Did work.",
            result_uri="uri://result.json",
        )
        sm.process_signal(output)

        snap = build_hud_snapshot(signal_manager=sm, thread_id="t1")
        nodes = snap["nodes"]
        assert len(nodes) >= 1
        worker = next(n for n in nodes if n["id"] == "worker_1")
        assert worker["status"] == "DONE"
        assert worker["last_signal"] == "DONE"
        assert "Did work" in worker.get("summary", "")

    def test_includes_implicit_links(self):
        """Data-flow links from requires → producer URIs should appear."""
        sm = SignalManager()
        output = ClawOutput(
            signal=Signal.DONE,
            node_id="producer",
            orchestrator_summary="Produced.",
            result_uri="uri://data.csv",
        )
        sm.process_signal(output)

        manifest_nodes = {
            "producer": {"requires": []},
            "consumer": {"requires": ["producer_result"]},
        }
        snap = build_hud_snapshot(
            signal_manager=sm,
            thread_id="t1",
            manifest_nodes=manifest_nodes,
        )
        links = snap.get("links", [])
        # Should have at least one implicit link from consumer → producer
        assert len(links) >= 1

    def test_empty_bag(self):
        """Empty SignalManager should return valid empty snapshot."""
        sm = SignalManager()
        snap = build_hud_snapshot(signal_manager=sm, thread_id="empty")
        assert snap["thread_id"] == "empty"
        assert snap["nodes"] == []
        assert snap["links"] == []
