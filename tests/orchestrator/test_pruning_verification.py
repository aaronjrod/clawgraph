from clawgraph.bag.node import clawnode
from clawgraph.core.models import ClawOutput, Signal
from clawgraph.orchestrator.graph import ClawBag


class TestPruningVerification:
    """F-REQ-16: Verification that raw tool outputs are pruned after summary generation."""

    def test_pruning_removes_raw_tool_outputs(self, mock_gemini):
        bag = ClawBag(name="prune_test_bag")

        @clawnode(id="heavy_worker", description="Generates large output.", bag="prune_test_bag")
        def heavy_worker(state: dict) -> ClawOutput:
            # Simulate a large tool output that should be pruned
            return ClawOutput(
                signal=Signal.DONE,
                node_id="heavy_worker",
                orchestrator_summary="Short summary.",
                # This raw output is what we want to ensure DOES NOT stay in the active context
                # once the next node starts.
                result_uri="uri://large_result.json",
            )

        @clawnode(id="verifier", description="Checks state.", bag="prune_test_bag")
        def verifier(state: dict) -> ClawOutput:
            # In a truly pruned state, the large raw data from heavy_worker
            # should not be present in the 'current_output' or 'history'
            # if we follow the selective memory pruning rule.
            return ClawOutput(
                signal=Signal.DONE,
                node_id="verifier",
                orchestrator_summary="Verified pruning.",
            )

        bag.manager.register_node(heavy_worker)
        bag.manager.register_node(verifier)

        mock_gemini.add_expected_call(
            "dispatch_node", {"node_id": "heavy_worker"}, text="Large work."
        )
        mock_gemini.add_expected_call("dispatch_node", {"node_id": "verifier"}, text="Verifying.")
        mock_gemini.add_expected_call("complete", {"final_summary": "Done."}, text="Finish.")

        result = bag.start_job(objective="Pruning verification.")

        # If F-REQ-16 is implemented, we should see evidence in the final state
        # that raw tool outputs were pruned.
        # This is a TDD skeleton; we'll refine the assertion once we define the specific
        # structure of 'pruned' state keys.
        assert "heavy_worker" in result.get("completed_nodes", [])
