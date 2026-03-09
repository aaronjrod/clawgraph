from clawgraph.bag.node import clawnode
from clawgraph.core.models import ClawOutput, Signal
from clawgraph.orchestrator.graph import ClawBag


class TestMaxIterations:
    """B-REQ-10: Enforcement of max_iterations to prevent infinite loops."""

    def test_max_iterations_terminates_loop(self, mock_gemini):
        # A node that always returns DONE but the goal is never reached (looping)
        bag = ClawBag(name="loop_bag", max_iterations=3)

        @clawnode(id="looper", description="Forever node.", bag="loop_bag")
        def looper(state: dict) -> ClawOutput:
            return ClawOutput(
                signal=Signal.DONE,
                node_id="looper",
                orchestrator_summary="Still looping...",
            )

        bag.manager.register_node(looper)

        # Mockgemini setup: Dispatch looper 3 times, then the orchestrator should stop.
        for _ in range(3):
            mock_gemini.add_expected_call(
                "dispatch_node", {"node_id": "looper"}, text="Still looping."
            )

        # We don't expect a 4th call to dispatch_node.
        # The job should finish with an escalation or a specific status.
        result = bag.start_job(objective="Never end.", max_iterations=3)

        assert result is not None
        # Check if the job finished instead of timing out or hanging
        # Usually, LangGraph or our orchestrator will stop after internal limit.
        # We want to verify it doesn't exceed 3 iterations.
        timeline = result.get("timeline", [])
        dispatches = [
            e for e in timeline if e.get("node_id") == "looper" and e.get("signal") == "RUNNING"
        ]
        assert len(dispatches) <= 3
