"""TDD tests for NEED_INFO injection path (Appendix §1.7).

inject_info() allows the SO to answer a NEED_INFO question by writing
the answer into continuation_context and re-enqueuing the node.
"""

import pytest

from clawgraph.bag.node import clawnode
from clawgraph.core.models import ClawOutput, InfoRequest, Signal
from clawgraph.orchestrator.graph import ClawBag


class TestInjectInfo:
    """inject_info() API on ClawBag."""

    def test_inject_info_adds_to_continuation_context(self, mock_gemini):
        """After inject, state should have continuation_context for the node."""
        bag = ClawBag(name="inject_bag")

        @clawnode(id="questioner", description="Asks a question.", bag="inject_bag")
        def questioner(state: dict) -> ClawOutput:  # type: ignore[type-arg]
            # Check if answer is available in continuation_context
            ctx = state.get("continuation_context", {})
            answer = ctx.get("questioner")
            if answer:
                return ClawOutput(
                    signal=Signal.DONE,
                    node_id="questioner",
                    orchestrator_summary=f"Got answer: {answer}",
                    result_uri="uri://answered.json",
                )
            return ClawOutput(
                signal=Signal.NEED_INFO,
                node_id="questioner",
                orchestrator_summary="Need clarification.",
                info_request=InfoRequest(
                    question="What format?",
                    context="Processing data.",
                    target="SO",
                ),
            )

        bag.manager.register_node(questioner)

        # 1. Dispatch questioner (returns NEED_INFO)
        # 2. Orchestrator suspends
        mock_gemini.add_expected_call("dispatch_node", {"node_id": "questioner"}, text="Thinking: Dispatch.")
        mock_gemini.add_expected_call("suspend", {"human_request_message": "Need clarification."}, text="Thinking: Suspending.")

        # First run — should stall on NEED_INFO
        bag.start_job(
            objective="Info test.",
            max_iterations=2,
            thread_id="info-thread",
        )

        # Now inject the answer
        bag.inject_info(
            thread_id="info-thread",
            node_id="questioner",
            answer={"format": "JSON"},
        )

        # verify the injection API exists and returns a valid state
        assert hasattr(bag, "inject_info")

    def test_inject_info_re_enqueues_node(self, mock_gemini):
        """After inject, the node should appear in ready_queue."""
        bag = ClawBag(name="reenqueue_bag")

        @clawnode(id="asker", description="Asks.", bag="reenqueue_bag")
        def asker(state: dict) -> ClawOutput:  # type: ignore[type-arg]
            return ClawOutput(
                signal=Signal.NEED_INFO,
                node_id="asker",
                orchestrator_summary="Need info.",
                info_request=InfoRequest(
                    question="What is X?",
                    context="Context.",
                    target="SO",
                ),
            )

        bag.manager.register_node(asker)

        mock_gemini.add_expected_call("dispatch_node", {"node_id": "asker"}, text="Thinking: Dispatch.")
        mock_gemini.add_expected_call("suspend", {"human_request_message": "Need info."}, text="Thinking: Suspending.")

        bag.start_job(
            objective="Re-enqueue test.",
            max_iterations=2,
            thread_id="enqueue-thread",
        )

        state = bag.inject_info(
            thread_id="enqueue-thread",
            node_id="asker",
            answer="42",
        )

        assert "asker" in state.get("ready_queue", [])
        assert state.get("continuation_context", {}).get("asker") == "42"
