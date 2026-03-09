"""Audit gap TDD tests -- Gaps 2, 3, 4, 5 adapted for LLM Orchestrator Tools."""

from typing import Any, cast

from clawgraph.bag.node import clawnode
from clawgraph.core.models import (
    AggregatorOutput,
    BranchResult,
    ClawOutput,
    ErrorDetail,
    FailureClass,
    Signal,
)
from clawgraph.orchestrator.graph import BagState, ClawBag
from clawgraph.orchestrator.llm_tools import OrchestratorTools


class TestGap2HITLContextInjection:
    def test_suspend_node_injects_timeline(self, mock_gemini):
        """Gap 2: Ensure the suspension tool is called with appropriate context."""
        bag = ClawBag(name="suspend_bag")

        @clawnode(id="gate", description="Suspension gate.", bag="suspend_bag")
        def gate(s):
            return ClawOutput(
                signal=Signal.HOLD_FOR_HUMAN,
                node_id="gate",
                orchestrator_summary="Waiting for human.",
                human_request={"message": "Needs human look."},
            )

        bag.manager.register_node(gate)

        # We expect the LLM to see the HOLD_FOR_HUMAN and decide to suspend.
        mock_gemini.add_expected_call(
            "suspend",
            {"human_request_message": "Needs human look."},
            text="Thinking: Node requested human input, so I will suspend.",
        )

        result = bag.start_job(objective="Test suspension context.")
        assert result.get("suspended") is True


class TestGap3EscalationPolicyEnforcement:
    def test_route_signal_respects_need_info_retries(self, mock_gemini):
        """Gap 3: LLM manages retries by choosing to dispatch again."""
        bag = ClawBag(name="retry_bag")

        @clawnode(id="flaky", description="Flaky node.", bag="retry_bag")
        def flaky(s):
            return ClawOutput(
                signal=Signal.NEED_INFO,
                node_id="flaky",
                orchestrator_summary="Need more info.",
                info_request={"question": "What is x?", "context": "x is needed for flaky."},
            )

        bag.manager.register_node(flaky)

        # 1. Dispatch flaky (returns NEED_INFO)
        # 2. Dispatch flaky again (returns NEED_INFO)
        # 3. Escalate (too many retries)
        mock_gemini.add_expected_call(
            "dispatch_node", {"node_id": "flaky"}, text="Thinking: Retrying once."
        )
        mock_gemini.add_expected_call(
            "dispatch_node", {"node_id": "flaky"}, text="Thinking: Retrying twice."
        )
        mock_gemini.add_expected_call(
            "escalate",
            {"reason": "Too many retries", "failure_class": "TOOL_FAILURE"},
            text="Thinking: I give up.",
        )

        result = bag.start_job(objective="Test retries.", max_iterations=5)
        assert "pending_escalation" in result


class TestGap4PartialCommitPolicy:
    def test_eager_partial_commit_registers_successes(self):
        """Gap 4: Eager policy commits DONE branches immediately even if root is PARTIAL."""
        bag = ClawBag(name="test_bag")
        tools = OrchestratorTools(bag_manager=bag.manager, signal_manager=bag.signal_manager)

        state: BagState = {"bag_name": "test_bag", "document_archive": {}, "timeline": []}

        # Mock result of a node that returns AggregatorOutput
        @clawnode(id="agg", description="Aggregator node.", bag="test_bag")
        def agg_node(s):
            return AggregatorOutput(
                signal=Signal.PARTIAL,
                node_id="agg",
                orchestrator_summary="Partial results.",
                result_uri="uri://agg_partial",
                error_detail=ErrorDetail(
                    failure_class=FailureClass.TOOL_FAILURE, message="One branch failed."
                ),
                partial_commit_policy="eager",
                branch_breakdown=[
                    BranchResult(
                        branch_id="b1",
                        node_id="n1",
                        signal=Signal.DONE,
                        summary="ok",
                        result_uri="uri://1",
                    ),
                    BranchResult(
                        branch_id="b2",
                        node_id="n2",
                        signal=Signal.FAILED,
                        summary="fail",
                        error_detail=ErrorDetail(
                            failure_class=FailureClass.LOGIC_ERROR, message="logic fail"
                        ),
                    ),
                ],
            )

        bag.manager.register_node(agg_node)

        updates = tools.dispatch_node(state, {"node_id": "agg"})
        archive = updates.get("document_archive", {})

        assert "b1_result" in archive
        assert archive["b1_result"]["uri"] == "uri://1"
        assert "b2_result" not in archive

    def test_atomic_partial_commit_delays_artifact_registration(self):
        """Gap 4: Atomic policy only commits when root is DONE."""
        bag = ClawBag(name="test_bag")
        tools = OrchestratorTools(bag_manager=bag.manager, signal_manager=bag.signal_manager)

        state: BagState = {"bag_name": "test_bag", "document_archive": {}, "timeline": []}

        @clawnode(id="agg", description="Atomic aggregator.", bag="test_bag")
        def agg_node(s):
            return AggregatorOutput(
                signal=Signal.PARTIAL,
                node_id="agg",
                orchestrator_summary="Partial results.",
                result_uri="uri://agg_partial",
                error_detail=ErrorDetail(
                    failure_class=FailureClass.TOOL_FAILURE, message="Partial result pending."
                ),
                partial_commit_policy="atomic",  # default
                branch_breakdown=[
                    BranchResult(
                        branch_id="b1",
                        node_id="n1",
                        signal=Signal.DONE,
                        summary="ok",
                        result_uri="uri://1",
                    )
                ],
            )

        bag.manager.register_node(agg_node)

        updates = tools.dispatch_node(state, {"node_id": "agg"})
        archive = updates.get("document_archive", {})

        assert "b1_result" not in archive  # Not DONE yet


class TestGap5MultiDomainTagVisibility:
    def test_prerequisite_checker_respects_domain_tags(self):
        """Gap 5 (F-REQ-17): Prerequisite resolution should respect domain tags.
        In the LLM architecture, we can still test the baseline visibility checking
        done inside OrchestratorTools.dispatch_node.
        """
        bag = ClawBag(name="test_bag")

        @clawnode(
            id="consumer_node",
            description="Consumes",
            bag="test_bag",
            requires=["secure_doc"],
        )
        def consumer_node(state: dict) -> ClawOutput:  # type: ignore[type-arg]
            return ClawOutput(
                signal=Signal.DONE,
                node_id="consumer_node",
                orchestrator_summary="OK",
                result_uri="uri://ok",
            )

        bag.manager.register_node(consumer_node)

        tools = OrchestratorTools(bag_manager=bag.manager, signal_manager=bag.signal_manager)

        # State with a document from another domain, not tagged public.
        state: BagState = {
            "bag_name": "test_bag",
            "current_node_id": "consumer_node",
            "document_archive": {
                "secure_doc": {
                    "uri": "s3://secure",
                    "domain": "other_bag",
                    "tags": ["internal"],
                }
            },
            "bag_manifest": bag.manager.manifest.model_dump(),
            "ready_queue": ["consumer_node"],
            "stalled_queue": [],
            "completed_nodes": [],
            "timeline": [],
        }

        updates = tools.dispatch_node(cast(dict[str, Any], state), {"node_id": "consumer_node"})
        output = updates.get("current_output", {})

        # It should stall because it cannot see the document.
        # The LLM tools will emit STALLED event and set output to signal=None.
        assert output.get("signal") is None
        assert "STALLED" in output.get("orchestrator_summary", "")
