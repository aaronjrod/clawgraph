"""TDD tests for PARTIAL prereq re-evaluation (Appendix §1.9).

PARTIAL signals with eager commit policy store artifacts, so they should
also trigger _resolve_stalled to unblock waiting consumers.
"""


from clawgraph.bag.node import clawnode
from clawgraph.core.models import (
    AggregatorOutput,
    BranchResult,
    ClawOutput,
    ErrorDetail,
    FailureClass,
    Signal,
)
from clawgraph.orchestrator.graph import ClawBag


class TestPartialResolve:
    """PARTIAL + eager commits should trigger prereq re-evaluation."""

    def test_partial_eager_resolves_stalled(self, mock_gemini):
        """Branch DONE in PARTIAL/eager should unblock a stalled consumer."""
        bag = ClawBag(name="partial_resolve_bag")

        @clawnode(id="aggregator", description="Fan-in gate.", bag="partial_resolve_bag")
        def aggregator(state: dict) -> ClawOutput:  # type: ignore[type-arg]
            return AggregatorOutput(
                signal=Signal.PARTIAL,
                node_id="aggregator",
                orchestrator_summary="Partial: lint passed, tests failed.",
                result_uri="uri://aggregated.json",
                partial_commit_policy="eager",
                error_detail=ErrorDetail(
                    failure_class=FailureClass.LOGIC_ERROR,
                    message="Tests failed.",
                ),
                branch_breakdown=[
                    BranchResult(
                        branch_id="lint",
                        node_id="lint_check",
                        signal=Signal.DONE,
                        summary="Lint passed.",
                        result_uri="uri://lint.json",
                    ),
                    BranchResult(
                        branch_id="tests",
                        node_id="test_runner",
                        signal=Signal.FAILED,
                        summary="Tests failed.",
                        error_detail=ErrorDetail(
                            failure_class=FailureClass.LOGIC_ERROR,
                            message="3 failures.",
                        ),
                    ),
                ],
            )

        @clawnode(
            id="lint_consumer",
            description="Uses lint results.",
            bag="partial_resolve_bag",
            requires=["lint_result"],
        )
        def lint_consumer(state: dict) -> ClawOutput:  # type: ignore[type-arg]
            return ClawOutput(
                signal=Signal.DONE,
                node_id="lint_consumer",
                orchestrator_summary="Consumed lint output.",
                result_uri="uri://lint_report.json",
            )

        bag.manager.register_node(aggregator)
        bag.manager.register_node(lint_consumer)

        mock_gemini.add_expected_call("dispatch_node", {"node_id": "aggregator"}, text="Thinking: Dispatch.")
        mock_gemini.add_expected_call("escalate", {"reason": "Partial failure.", "failure_class": "LOGIC_ERROR"}, text="Thinking: Escalating.")

        result = bag.start_job(objective="Partial resolve.", max_iterations=10)

        # lint_consumer should have been unblocked (moved from stalled to ready)
        # even though the graph terminates at PARTIAL escalation.
        stalled = result.get("stalled_queue", [])
        assert "lint_consumer" not in stalled, (
            "lint_consumer should not be stalled after PARTIAL eager commit"
        )

    def test_partial_atomic_does_not_resolve(self, mock_gemini):
        """PARTIAL with atomic policy should NOT unblock stalled consumers."""
        bag = ClawBag(name="atomic_bag")

        @clawnode(id="atomic_agg", description="Atomic aggregator.", bag="atomic_bag")
        def atomic_agg(state: dict) -> ClawOutput:  # type: ignore[type-arg]
            return AggregatorOutput(
                signal=Signal.PARTIAL,
                node_id="atomic_agg",
                orchestrator_summary="Partial: atomic mode.",
                result_uri="uri://atomic.json",
                partial_commit_policy="atomic",
                error_detail=ErrorDetail(
                    failure_class=FailureClass.LOGIC_ERROR,
                    message="Mixed results.",
                ),
                branch_breakdown=[
                    BranchResult(
                        branch_id="branch_a",
                        node_id="worker_a",
                        signal=Signal.DONE,
                        summary="Done.",
                        result_uri="uri://a.json",
                    ),
                    BranchResult(
                        branch_id="branch_b",
                        node_id="worker_b",
                        signal=Signal.FAILED,
                        summary="Failed.",
                        error_detail=ErrorDetail(
                            failure_class=FailureClass.LOGIC_ERROR,
                            message="Fail.",
                        ),
                    ),
                ],
            )

        @clawnode(
            id="atomic_consumer",
            description="Needs branch_a_result.",
            bag="atomic_bag",
            requires=["branch_a_result"],
        )
        def atomic_consumer(state: dict) -> ClawOutput:  # type: ignore[type-arg]
            return ClawOutput(
                signal=Signal.DONE,
                node_id="atomic_consumer",
                orchestrator_summary="Consumed.",
                result_uri="uri://consumed.json",
            )

        bag.manager.register_node(atomic_agg)
        bag.manager.register_node(atomic_consumer)

        mock_gemini.add_expected_call("dispatch_node", {"node_id": "atomic_agg"}, text="Thinking: Dispatch.")
        mock_gemini.add_expected_call("escalate", {"reason": "Partial failure.", "failure_class": "LOGIC_ERROR"}, text="Thinking: Escalating.")

        result = bag.start_job(objective="Atomic no-resolve.", max_iterations=5)

        # atomic_consumer should still be stalled (no commit in atomic mode)
        assert "atomic_consumer" in result.get("stalled_queue", []), (
            "atomic_consumer should remain stalled under atomic policy"
        )
