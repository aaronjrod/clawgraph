"""TDD tests for memory pruning (F-REQ-16).

After a node completes with DONE, current_output should be cleared to
prevent raw output blobs from accumulating in state.
"""

from clawgraph.bag.node import clawnode
from clawgraph.core.models import ClawOutput, Signal
from clawgraph.orchestrator.graph import ClawBag


class TestMemoryPruning:
    """current_output pruning after DONE."""

    def test_current_output_pruned_after_done(self):
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
            current = state.get("current_output", {})
            # The orchestrator_summary from step_one should NOT be in current_output
            assert current.get("node_id") != "step_one", (
                "current_output should have been pruned between dispatches"
            )
            return ClawOutput(
                signal=Signal.DONE,
                node_id="step_two",
                orchestrator_summary="Step two done.",
                result_uri="uri://s2.json",
            )

        bag.manager.register_node(step_one)
        bag.manager.register_node(step_two)

        result = bag.start_job(objective="Pruning test.", max_iterations=10)

        # Both steps should have run
        assert "step_one" in call_order
        assert "step_two" in call_order

    def test_phase_history_preserves_summaries(self):
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

        result = bag.start_job(objective="History test.", max_iterations=10)

        history = result.get("phase_history", [])
        assert len(history) >= 2
        assert "A completed." in history
        assert "B completed." in history
