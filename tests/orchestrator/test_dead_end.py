"""TDD tests for STALLED dead-end cascading (Appendix §1.2).

When a producer node FAILs, consumers whose prerequisites can never be
satisfied should be cascaded to FAILED instead of staying in stalled_queue.
"""


from clawgraph.bag.node import clawnode
from clawgraph.core.models import (
    ClawOutput,
    ErrorDetail,
    FailureClass,
    Signal,
)
from clawgraph.orchestrator.graph import ClawBag


class TestDeadEndCascade:
    """STALLED consumers of a FAILED producer should cascade to FAILED."""

    def test_failed_producer_cascades_stalled_consumers(self, mock_gemini):
        """Consumer depending on failed producer's result gets removed from stalled."""
        bag = ClawBag(name="dead_end_bag")

        @clawnode(id="producer", description="Produces data.", bag="dead_end_bag")
        def producer(state: dict) -> ClawOutput:  # type: ignore[type-arg]
            return ClawOutput(
                signal=Signal.FAILED,
                node_id="producer",
                orchestrator_summary="Producer crashed.",
                error_detail=ErrorDetail(
                    failure_class=FailureClass.TOOL_FAILURE,
                    message="External API down.",
                ),
            )

        @clawnode(
            id="consumer",
            description="Consumes producer output.",
            bag="dead_end_bag",
            requires=["producer_result"],
        )
        def consumer(state: dict) -> ClawOutput:  # type: ignore[type-arg]
            return ClawOutput(
                signal=Signal.DONE,
                node_id="consumer",
                orchestrator_summary="Consumed data.",
                result_uri="uri://consumed.json",
            )

        bag.manager.register_node(producer)
        bag.manager.register_node(consumer)

        # 1. Dispatch producer (fails)
        # 2. Orchestrator detects failure, cascades consumer to FAILED (DEAD_END)
        # 3. Escalates
        mock_gemini.add_expected_call("dispatch_node", {"node_id": "producer"}, text="Thinking: Dispatching producer.")
        mock_gemini.add_expected_call("escalate", {"reason": "Producer failed, cannot continue.", "failure_class": "TOOL_FAILURE"}, text="Thinking: Producer failed. I'll check stalled nodes... consumer is blocked. Cascading.")

        result = bag.start_job(objective="Dead end test.", max_iterations=5)

        # Consumer should NOT be in stalled_queue (cascaded out).
        assert "consumer" not in result.get("stalled_queue", [])
        assert len(result.get("stalled_queue", [])) == 0
        # Consumer should appear in completed_nodes (as a cascaded failure).
        completed = result.get("completed_nodes", [])
        assert "consumer" in completed
        assert len(completed) == 1  # only consumer (DEAD_END)

    def test_failed_producer_does_not_cascade_unrelated_nodes(self, mock_gemini):
        """Stalled nodes depending on OTHER artifacts should stay stalled."""
        bag = ClawBag(name="unrelated_bag")

        @clawnode(id="failing_node", description="Fails.", bag="unrelated_bag")
        def failing_node(state: dict) -> ClawOutput:  # type: ignore[type-arg]
            return ClawOutput(
                signal=Signal.FAILED,
                node_id="failing_node",
                orchestrator_summary="Failed.",
                error_detail=ErrorDetail(
                    failure_class=FailureClass.LOGIC_ERROR,
                    message="Bad logic.",
                ),
            )

        @clawnode(
            id="unrelated_consumer",
            description="Waits on different artifact.",
            bag="unrelated_bag",
            requires=["totally_different_artifact"],
        )
        def unrelated_consumer(state: dict) -> ClawOutput:  # type: ignore[type-arg]
            return ClawOutput(
                signal=Signal.DONE,
                node_id="unrelated_consumer",
                orchestrator_summary="Done.",
                result_uri="uri://done.json",
            )

        bag.manager.register_node(failing_node)
        bag.manager.register_node(unrelated_consumer)

        mock_gemini.add_expected_call("dispatch_node", {"node_id": "failing_node"}, text="Thinking: This node failed.")
        mock_gemini.add_expected_call("escalate", {"reason": "Logic error.", "failure_class": "LOGIC_ERROR"}, text="Thinking: Failing node failed. Unrelated consumer is still stalled on something else.")

        result = bag.start_job(objective="Selective cascade.", max_iterations=5)

        # Unrelated consumer should still be stalled (not cascaded).
        stalled = result.get("stalled_queue", [])
        assert "unrelated_consumer" in stalled
        assert len(stalled) == 1
        assert len(result.get("completed_nodes", [])) == 0  # failing_node does not enter completed

    def test_cascade_emits_timeline_event(self, mock_gemini):
        """Dead-end cascading should emit a DEAD_END timeline event."""
        bag = ClawBag(name="timeline_bag")

        @clawnode(id="doomed_producer", description="Will fail.", bag="timeline_bag")
        def doomed_producer(state: dict) -> ClawOutput:  # type: ignore[type-arg]
            return ClawOutput(
                signal=Signal.FAILED,
                node_id="doomed_producer",
                orchestrator_summary="Doomed.",
                error_detail=ErrorDetail(
                    failure_class=FailureClass.SYSTEM_CRASH,
                    message="Crash.",
                ),
            )

        @clawnode(
            id="doomed_consumer",
            description="Depends on doomed producer.",
            bag="timeline_bag",
            requires=["doomed_producer_result"],
        )
        def doomed_consumer(state: dict) -> ClawOutput:  # type: ignore[type-arg]
            return ClawOutput(
                signal=Signal.DONE,
                node_id="doomed_consumer",
                orchestrator_summary="Done.",
                result_uri="uri://ok.json",
            )

        bag.manager.register_node(doomed_producer)
        bag.manager.register_node(doomed_consumer)

        mock_gemini.add_expected_call("dispatch_node", {"node_id": "doomed_producer"}, text="Thinking: Producer failure.")
        mock_gemini.add_expected_call("escalate", {"reason": "System crash", "failure_class": "SYSTEM_CRASH"}, text="Thinking: Escalating.")

        result = bag.start_job(objective="Timeline test.", max_iterations=5)

        timeline = result.get("timeline", [])
        dead_end_events = [e for e in timeline if e.get("signal") == "DEAD_END"]
        assert len(dead_end_events) == 1, "Should have exactly one DEAD_END timeline event"
        assert dead_end_events[0]["node_id"] == "doomed_consumer"

    def test_cascade_marks_nodes_completed(self, mock_gemini):
        """Cascaded nodes should appear in completed_nodes."""
        bag = ClawBag(name="completed_bag")

        @clawnode(id="breaker", description="Breaks.", bag="completed_bag")
        def breaker(state: dict) -> ClawOutput:  # type: ignore[type-arg]
            return ClawOutput(
                signal=Signal.FAILED,
                node_id="breaker",
                orchestrator_summary="Broke.",
                error_detail=ErrorDetail(
                    failure_class=FailureClass.LOGIC_ERROR,
                    message="Broken.",
                ),
            )

        @clawnode(
            id="dep_a",
            description="Depends on breaker.",
            bag="completed_bag",
            requires=["breaker_result"],
        )
        def dep_a(state: dict) -> ClawOutput:  # type: ignore[type-arg]
            return ClawOutput(
                signal=Signal.DONE,
                node_id="dep_a",
                orchestrator_summary="Done.",
                result_uri="uri://a.json",
            )

        @clawnode(
            id="dep_b",
            description="Also depends on breaker.",
            bag="completed_bag",
            requires=["breaker_result"],
        )
        def dep_b(state: dict) -> ClawOutput:  # type: ignore[type-arg]
            return ClawOutput(
                signal=Signal.DONE,
                node_id="dep_b",
                orchestrator_summary="Done.",
                result_uri="uri://b.json",
            )

        bag.manager.register_node(breaker)
        bag.manager.register_node(dep_a)
        bag.manager.register_node(dep_b)

        mock_gemini.add_expected_call("dispatch_node", {"node_id": "breaker"}, text="Thinking: Breaker failed.")
        mock_gemini.add_expected_call("escalate", {"reason": "Breaking cascade.", "failure_class": "LOGIC_ERROR"}, text="Thinking: Cascading dep_a and dep_b.")

        result = bag.start_job(objective="Multi-cascade.", max_iterations=5)

        completed = result.get("completed_nodes", [])
        assert "dep_a" in completed
        assert "dep_b" in completed
        assert len(completed) == 2  # dep_a, dep_b (breaker FAILED so not included)
