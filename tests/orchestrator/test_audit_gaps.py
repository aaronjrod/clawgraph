"""Audit gap TDD tests -- Gaps 2, 3, 4, 5."""

import pytest

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
from clawgraph.orchestrator.hub import (
    ROUTE_ESCALATE,
    _make_dispatch_node,
    _make_suspend_node,
    route_signal,
)


class TestGap2HITLContextInjection:
    def test_suspend_node_injects_timeline(self):
        """Gap 2 (F-REQ-32): suspend node should inject timeline events into human_request."""
        from clawgraph.core.timeline import TimelineBuffer

        delivered: list[dict] = []  # type: ignore[type-arg]

        def handler(tid: str, req: dict) -> None:  # type: ignore[type-arg]
            delivered.append(req)

        # Create a TimelineBuffer with some events for context.
        timeline = TimelineBuffer()
        timeline.record_signal(
            thread_id="test_thread",
            output=ClawOutput(
                signal=Signal.DONE,
                node_id="prev_node",
                orchestrator_summary="Preceding work completed.",
                result_uri="uri://prev",
            ),
        )

        suspend = _make_suspend_node(hitl_handler=handler, timeline_buffer=timeline)

        state: BagState = {  # type: ignore[typeddict-item]
            "current_output": {
                "signal": Signal.HOLD_FOR_HUMAN,
                "human_request": {"message": "approve deployment?"},
            },
            "thread_id": "test_thread",
        }
        suspend(state)

        assert len(delivered) == 1
        # The handler should receive a payload augmented with context.
        assert "timeline_context" in delivered[0]
        assert len(delivered[0]["timeline_context"]) >= 1


class TestGap3EscalationPolicyEnforcement:
    def test_route_signal_respects_need_info_retries(self):
        """Gap 3 (F-REQ-10): NEED_INFO should not escalate until max_retries is exhausted."""
        state: BagState = {  # type: ignore[typeddict-item]
            "current_output": {"signal": Signal.NEED_INFO, "node_id": "need_info_node"},
            "iteration_count": 1,
            "max_iterations": 10,
            "need_info_tracking": {"need_info_node": {"retries": 0}},
        }
        # First time shouldn't escalate immediately if policy allows retries
        assert route_signal(state) != ROUTE_ESCALATE


class TestGap4PartialCommitPolicy:
    def test_eager_partial_commit_registers_successes(self):
        """Gap 4 (F-REQ-13): partial_commit_policy='eager' commits successful branches."""
        bag = ClawBag(name="test_bag")

        @clawnode(id="agg_node", description="Aggregates", bag="test")
        def agg_node(state: dict) -> ClawOutput:  # type: ignore[type-arg]
            return AggregatorOutput(
                signal=Signal.PARTIAL,
                node_id="agg_node",
                orchestrator_summary="Partial completion",
                result_uri="uri://agg.json",
                partial_commit_policy="eager",
                error_detail=ErrorDetail(
                    failure_class=FailureClass.TOOL_FAILURE, message="Failed."
                ),
                branch_breakdown=[
                    BranchResult(
                        branch_id="b1",
                        node_id="w1",
                        signal=Signal.DONE,
                        summary="OK",
                        result_uri="uri://b1.json",
                    )
                ],
            )

        bag.manager.register_node(agg_node)
        result = bag.start_job(objective="Test eager commit")

        archive = result.get("document_archive", {})
        assert "b1_result" in archive, (
            "Eager policy violated: branch result was not committed despite DONE signal."
        )

    def test_atomic_partial_commit_delays_artifact_registration(self):
        """Gap 4 (F-REQ-13): partial_commit_policy='atomic' delays commit."""
        bag = ClawBag(name="test_bag")

        @clawnode(id="agg_node", description="Aggregates", bag="test")
        def agg_node(state: dict) -> ClawOutput:  # type: ignore[type-arg]
            return AggregatorOutput(
                signal=Signal.PARTIAL,
                node_id="agg_node",
                orchestrator_summary="Partial completion",
                result_uri="uri://agg.json",
                partial_commit_policy="atomic",
                error_detail=ErrorDetail(
                    failure_class=FailureClass.TOOL_FAILURE, message="Failed."
                ),
                branch_breakdown=[
                    BranchResult(
                        branch_id="b1",
                        node_id="w1",
                        signal=Signal.DONE,
                        summary="OK",
                        result_uri="uri://b1.json",
                    )
                ],
            )

        bag.manager.register_node(agg_node)
        result = bag.start_job(objective="Test atomic commit")

        archive = result.get("document_archive", {})
        assert "b1_result" not in archive, (
            "Atomic policy violated: branch result committed despite PARTIAL signal."
        )


@pytest.mark.xfail(reason="Gap 5 deferred to Phase 8: domain-tag visibility not yet implemented")
class TestGap5MultiDomainTagVisibility:
    def test_prerequisite_checker_respects_domain_tags(self):
        """Gap 5 (F-REQ-17): Prerequisite resolution should respect domain tags."""
        bag = ClawBag(name="test_bag")

        @clawnode(
            id="consumer_node",
            description="Consumes",
            bag="test",
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

        dispatch = _make_dispatch_node(
            bag_manager=bag.manager, signal_manager=bag.signal_manager
        )

        # State with a document from another domain, not tagged public.
        state: BagState = {  # type: ignore[typeddict-item]
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

        updates = dispatch(state)
        output = updates.get("current_output", {})

        # It should stall/fail because it cannot see the document.
        assert output.get("signal") != Signal.DONE, (
            "Node executed but should have been blocked by visibility rules."
        )
