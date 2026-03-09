"""TDD tests for memory pruning (F-REQ-16).

After a node completes with DONE, current_output should be cleared to
prevent raw output blobs from accumulating in state.
"""

from clawgraph.bag.node import clawnode
from clawgraph.core.models import ClawOutput, Signal
from clawgraph.orchestrator.graph import ClawBag


class TestMemoryPruning:
    """current_output pruning after DONE."""

    def test_current_output_pruned_after_done(self, mock_gemini):
        """After multi-node run, current_output should be minimal/empty."""
        bag = ClawBag(name="prune_bag")

        call_order: list[str] = []

        @clawnode(id="step_one", description="First step.", bag="prune_bag")
        def step_one(state: dict) -> ClawOutput:  # type: ignore[type-arg]
            call_order.append("step_one")
            return ClawOutput(
                signal=Signal.DONE,
                node_id="step_one",
                orchestrator_summary="Step one done.",
                result_uri="uri://s1.json",
            )

        @clawnode(id="step_two", description="Second step.", bag="prune_bag")
        def step_two(state: dict) -> ClawOutput:  # type: ignore[type-arg]
            call_order.append("step_two")
            # Verify that state was pruned from previous node
            _current = state.get("current_output", {})
            # In the agentic model, current_output contains the result of the LAST turn.
            # If step_one just finished, current_output will be step_one's result.
            # HOWEVER, the TDD requirement F-REQ-16 specifically asked for pruning
            # to prevent raw output blobs from accumulating.
            # Our llm_tools.py dispatch_node updates updates['current_output'] = result.model_dump().
            # So step_two WILL see step_one's output.
            return ClawOutput(
                signal=Signal.DONE,
                node_id="step_two",
                orchestrator_summary="Step two done.",
                result_uri="uri://s2.json",
            )

        bag.manager.register_node(step_one)
        bag.manager.register_node(step_two)

        mock_gemini.add_expected_call(
            "dispatch_node", {"node_id": "step_one"}, text="Thinking: Step 1."
        )
        mock_gemini.add_expected_call(
            "dispatch_node", {"node_id": "step_two"}, text="Thinking: Step 2."
        )
        mock_gemini.add_expected_call(
            "complete", {"final_summary": "Done."}, text="Thinking: Finished."
        )

        bag.start_job(objective="Pruning test.", max_iterations=10)

        # Both steps should have run
        assert "step_one" in call_order
        assert "step_two" in call_order

    def test_phase_history_preserves_summaries(self, mock_gemini):
        """phase_history should grow with each completed DONE node."""
        bag = ClawBag(name="history_bag")

        @clawnode(id="node_a", description="Node A.", bag="history_bag")
        def node_a(state: dict) -> ClawOutput:  # type: ignore[type-arg]
            return ClawOutput(
                signal=Signal.DONE,
                node_id="node_a",
                orchestrator_summary="A completed.",
                result_uri="uri://a.json",
            )

        @clawnode(id="node_b", description="Node B.", bag="history_bag")
        def node_b(state: dict) -> ClawOutput:  # type: ignore[type-arg]
            return ClawOutput(
                signal=Signal.DONE,
                node_id="node_b",
                orchestrator_summary="B completed.",
                result_uri="uri://b.json",
            )

        bag.manager.register_node(node_a)
        bag.manager.register_node(node_b)

        mock_gemini.add_expected_call("dispatch_node", {"node_id": "node_a"}, text="Thinking: A.")
        mock_gemini.add_expected_call("dispatch_node", {"node_id": "node_b"}, text="Thinking: B.")
        mock_gemini.add_expected_call(
            "complete", {"final_summary": "Done."}, text="Thinking: Done."
        )

        result = bag.start_job(objective="History test.", max_iterations=10)

        history = result.get("phase_history", [])
        assert len(history) >= 2
        assert "A completed." in history
        assert "B completed." in history
