"""TDD tests for BagContract model and validation (F-REQ-25).

BagContract defines strict I/O schemas per bag, validated at start_job
(inputs) and at dispatch_node (outputs).
"""

import pytest

from clawgraph.bag.node import clawnode
from clawgraph.core.exceptions import BagContractError
from clawgraph.core.models import BagContract, ClawOutput, Signal
from clawgraph.orchestrator.graph import ClawBag


class TestBagContract:
    """BagContract validation at start_job and dispatch."""

    def test_bag_contract_validates_inputs_at_start(self):
        """start_job() with missing required inputs should raise BagContractError."""
        contract = BagContract(required_inputs=["source_doc", "config"])
        bag = ClawBag(name="contract_bag", contract=contract)

        @clawnode(id="noop", description="No-op.", bag="contract_bag")
        def noop(state: dict) -> ClawOutput:  # type: ignore[type-arg]
            return ClawOutput(
                signal=Signal.DONE,
                node_id="noop",
                orchestrator_summary="Done.",
                result_uri="uri://out.json",
            )

        bag.manager.register_node(noop)

        with pytest.raises(BagContractError, match="source_doc"):
            bag.start_job(
                objective="Should fail.",
                inputs={"config": "uri://config.json"},
            )

    def test_bag_contract_passes_valid_inputs(self):
        """start_job() with all required inputs should succeed."""
        contract = BagContract(required_inputs=["source_doc"])
        bag = ClawBag(name="valid_contract_bag", contract=contract)

        @clawnode(id="reader", description="Reads.", bag="valid_contract_bag")
        def reader(state: dict) -> ClawOutput:  # type: ignore[type-arg]
            return ClawOutput(
                signal=Signal.DONE,
                node_id="reader",
                orchestrator_summary="Read doc.",
                result_uri="uri://summary.txt",
            )

        bag.manager.register_node(reader)

        result = bag.start_job(
            objective="Should pass.",
            inputs={"source_doc": "uri://doc.pdf"},
        )
        assert result is not None

    def test_bag_contract_validates_output_signals(self):
        """Node emitting a signal not in allowed_signals should be caught."""
        contract = BagContract(allowed_signals=[Signal.DONE, Signal.FAILED])
        bag = ClawBag(name="signal_contract_bag", contract=contract)

        @clawnode(id="hold_node", description="Holds.", bag="signal_contract_bag")
        def hold_node(state: dict) -> ClawOutput:  # type: ignore[type-arg]
            from clawgraph.core.models import HumanRequest

            return ClawOutput(
                signal=Signal.HOLD_FOR_HUMAN,
                node_id="hold_node",
                orchestrator_summary="Need approval.",
                human_request=HumanRequest(message="Approve?"),
            )

        bag.manager.register_node(hold_node)

        result = bag.start_job(objective="Signal violation.", max_iterations=3)

        # The output should be a contract violation (synthesized FAILED)
        output = result.get("current_output", {})
        assert output.get("orchestrator_synthesized") is True, (
            "Contract violation should produce a synthesized error"
        )

    def test_bag_contract_default_is_permissive(self):
        """No contract set → no validation (backwards compat)."""
        bag = ClawBag(name="no_contract_bag")

        @clawnode(id="anything", description="Anything goes.", bag="no_contract_bag")
        def anything(state: dict) -> ClawOutput:  # type: ignore[type-arg]
            return ClawOutput(
                signal=Signal.DONE,
                node_id="anything",
                orchestrator_summary="Done.",
                result_uri="uri://out.json",
            )

        bag.manager.register_node(anything)

        # Should succeed without any contract
        result = bag.start_job(objective="No contract.", inputs={})
        assert result is not None

    def test_bag_contract_serializes_to_manifest(self):
        """Contract should be accessible via the bag."""
        contract = BagContract(
            required_inputs=["doc"],
            required_outputs=["result_uri"],
            allowed_signals=[Signal.DONE, Signal.FAILED],
        )
        bag = ClawBag(name="manifest_bag", contract=contract)

        assert bag.contract is not None
        assert "doc" in bag.contract.required_inputs
        assert Signal.DONE in (bag.contract.allowed_signals or [])
