"""TDD tests for state drift detection (F-REQ-24).

When a node returns a ClawOutput with a mismatched node_id, the Orchestrator
should synthesize NEED_INTERVENTION with SCHEMA_MISMATCH.
"""

from clawgraph.bag.node import clawnode
from clawgraph.core.models import ClawOutput, FailureClass, Signal
from clawgraph.orchestrator.graph import ClawBag


class TestStateDrift:
    """State drift detection via node_id mismatch."""

    def test_node_id_mismatch_triggers_intervention(self):
        """Node returning wrong node_id → synthesized NEED_INTERVENTION."""
        bag = ClawBag(name="drift_bag")

        @clawnode(id="honest_node", description="Returns wrong ID.", bag="drift_bag")
        def honest_node(state: dict) -> ClawOutput:  # type: ignore[type-arg]
            return ClawOutput(
                signal=Signal.DONE,
                node_id="IMPOSTER_NODE",  # Wrong ID!
                orchestrator_summary="I'm someone else.",
                result_uri="uri://fake.json",
            )

        bag.manager.register_node(honest_node)
        result = bag.start_job(objective="Drift test.")

        output = result.get("current_output", {})
        assert output.get("orchestrator_synthesized") is True, (
            "Mismatched node_id should produce a synthesized error"
        )
        assert output.get("signal") == Signal.NEED_INTERVENTION.value
        error = output.get("error_detail", {})
        assert error.get("failure_class") == FailureClass.SCHEMA_MISMATCH.value

    def test_correct_node_id_passes(self):
        """Normal execution with matching node_id → no drift."""
        bag = ClawBag(name="clean_bag")

        @clawnode(id="good_node", description="Returns correct ID.", bag="clean_bag")
        def good_node(state: dict) -> ClawOutput:  # type: ignore[type-arg]
            return ClawOutput(
                signal=Signal.DONE,
                node_id="good_node",
                orchestrator_summary="All good.",
                result_uri="uri://ok.json",
            )

        bag.manager.register_node(good_node)
        result = bag.start_job(objective="Clean test.")

        output = result.get("current_output", {})
        assert output.get("orchestrator_synthesized") is not True
        assert output.get("signal") == Signal.DONE.value
