"""TDD tests for state drift detection (F-REQ-24).

When a node returns a ClawOutput with a mismatched node_id, the Orchestrator
should synthesize NEED_INTERVENTION with SCHEMA_MISMATCH.
"""

from clawgraph.bag.node import clawnode
from clawgraph.core.models import ClawOutput, FailureClass, Signal
from clawgraph.orchestrator.graph import ClawBag


class TestStateDrift:
    """State drift detection via node_id mismatch."""

    def test_node_id_mismatch_triggers_intervention(self, mock_gemini):
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
        
        # 1. Dispatch honest_node (logic detects mismatch, returns NEED_INTERVENTION)
        # 2. Orchestrator sees NEED_INTERVENTION and should escalate.
        mock_gemini.add_expected_call("dispatch_node", {"node_id": "honest_node"}, text="Thinking: Dispatching the node.")
        mock_gemini.add_expected_call("escalate", {"reason": "State drift detected.", "failure_class": "SCHEMA_MISMATCH"}, text="Thinking: I detected a node ID mismatch, which is a schema violation.")
        
        result = bag.start_job(objective="Drift test.")

        assert "pending_escalation" in result
        esc = result["pending_escalation"]
        assert esc["signal"] == "NEED_INTERVENTION"
        assert esc["error_detail"]["failure_class"] == FailureClass.SCHEMA_MISMATCH.value

    def test_correct_node_id_passes(self, mock_gemini):
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
        
        mock_gemini.add_expected_call("dispatch_node", {"node_id": "good_node"}, text="Thinking: Dispatching good node.")
        mock_gemini.add_expected_call("complete", {"final_summary": "Done."}, text="Thinking: Finished.")
        
        result = bag.start_job(objective="Clean test.")

        output = result.get("current_output", {})
        assert output.get("orchestrator_synthesized") is not True
        assert output.get("signal") == Signal.DONE.value
