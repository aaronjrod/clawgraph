from clawgraph.bag.node import clawnode
from clawgraph.core.models import ClawOutput, Signal
from clawgraph.orchestrator.graph import ClawBag


class TestHUDSnapshot:
    """F-REQ-29: Verification of the get_hud_snapshot() API."""

    def test_get_hud_snapshot_contains_manifest_and_signals(self, mock_gemini):
        bag = ClawBag(name="hud_bag")

        @clawnode(id="worker", description="HUD worker.", bag="hud_bag")
        def worker(state: dict) -> ClawOutput:
            return ClawOutput(
                signal=Signal.DONE,
                node_id="worker",
                orchestrator_summary="HUD update.",
                result_uri="uri://hud.json",
            )

        bag.manager.register_node(worker)

        # Before job starts
        snapshot = bag.get_hud_snapshot()
        assert "nodes" in snapshot
        assert any(n["id"] == "worker" for n in snapshot["nodes"])

        # Mock run to get live status
        mock_gemini.add_expected_call("dispatch_node", {"node_id": "worker"}, text="Work.")
        mock_gemini.add_expected_call("complete", {"final_summary": "Done."}, text="Finish.")

        result = bag.start_job(objective="Test HUD.", thread_id="hud-thread")

        # After job starts/completes
        snapshot_alive = bag.get_hud_snapshot(thread_id="hud-thread")
        assert "nodes" in snapshot_alive

        worker_node = next(n for n in snapshot_alive["nodes"] if n["id"] == "worker")
        assert worker_node["status"] == "DONE"
        assert "HUD update" in worker_node["summary"]
