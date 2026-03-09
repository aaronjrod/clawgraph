"""Tests for ClawBag — setup, compilation, execution, repr, audit/rollback, summary."""

import pytest

from conftest import (
    crashing_node,
    failing_node,
    hold_node,
    success_node,
)

from clawgraph.bag.node import clawnode
from clawgraph.core.models import ClawOutput, Signal
from clawgraph.orchestrator.graph import ClawBag


# ── ClawBag Setup Tests ──────────────────────────────────────────────────────


class TestClawBagSetup:
    def test_creation(self):
        bag = ClawBag(name="test_bag")
        assert bag.name == "test_bag"
        assert len(bag.manager) == 0

    def test_register_node_via_manager(self):
        bag = ClawBag(name="test_bag")
        bag.manager.register_node(success_node)
        assert "success_node" in bag.manager

    def test_hitl_handler_registration(self):
        bag = ClawBag(name="test_bag")

        def my_handler(thread_id: str, request: dict) -> None:  # type: ignore[type-arg]
            pass

        bag.register_hitl_handler(my_handler)
        assert bag._hitl_handler is my_handler


# ── ClawBag Compilation Tests ────────────────────────────────────────────────


class TestClawBagCompilation:
    def test_compile_graph(self):
        bag = ClawBag(name="test_bag")
        bag.manager.register_node(success_node)
        graph = bag.compile_graph()
        assert graph is not None
        assert bag.is_compiled

    def test_lazy_compilation_skips_when_clean(self):
        bag = ClawBag(name="test_bag")
        bag.manager.register_node(success_node)
        bag.compile_graph()
        assert not bag.is_dirty
        # Second call should return cached graph.
        graph2 = bag.compile_graph_if_dirty()
        assert graph2 is not None

    def test_lazy_compilation_recompiles_when_dirty(self):
        bag = ClawBag(name="test_bag")
        bag.manager.register_node(success_node)
        bag.compile_graph()

        # Mutate the manifest — graph becomes dirty.
        bag.manager.register_node(failing_node)
        assert bag.is_dirty

        graph2 = bag.compile_graph_if_dirty()
        assert graph2 is not None
        assert not bag.is_dirty


# ── ClawBag Execution Tests ──────────────────────────────────────────────────


class TestClawBagExecution:
    def test_start_job_success(self, mock_gemini):
        bag = ClawBag(name="test_bag")
        bag.manager.register_node(success_node)
        
        mock_gemini.add_expected_call("dispatch_node", {"node_id": "success_node"}, text="Thinking: Dispatch.")
        mock_gemini.add_expected_call("complete", {"final_summary": "Done."}, text="Thinking: Done.")

        result = bag.start_job(objective="Test run.", inputs={})

        assert result is not None
        output = result.get("current_output", {})
        assert output.get("signal") == Signal.DONE

    def test_start_job_locks_and_unlocks(self, mock_gemini):
        bag = ClawBag(name="test_bag")
        bag.manager.register_node(success_node)

        mock_gemini.add_expected_call("dispatch_node", {"node_id": "success_node"}, text="Thinking: Dispatch.")
        mock_gemini.add_expected_call("complete", {"final_summary": "Done."}, text="Thinking: Done.")

        assert not bag.manager._locked
        bag.start_job(objective="Test locking.")
        assert not bag.manager._locked  # Unlocked after job completes.

    def test_start_job_with_failing_node(self, mock_gemini):
        bag = ClawBag(name="test_bag")
        bag.manager.register_node(failing_node)
        
        mock_gemini.add_expected_call("dispatch_node", {"node_id": "failing_node"}, text="Thinking: Dispatch.")
        mock_gemini.add_expected_call("escalate", {"reason": "Node failed.", "failure_class": "LOGIC_ERROR"}, text="Thinking: Escalating.")

        result = bag.start_job(objective="Fail test.")
        assert "pending_escalation" in result
        esc = result["pending_escalation"]
        assert esc["signal"] == "NEED_INTERVENTION"
        assert esc["error_detail"]["failure_class"] == "LOGIC_ERROR"

    # Exception interception: unhandled exceptions -> synthesized FAILED.
    def test_start_job_with_crashing_node(self, mock_gemini):
        bag = ClawBag(name="test_bag")
        bag.manager.register_node(crashing_node)

        mock_gemini.add_expected_call("dispatch_node", {"node_id": "crashing_node"}, text="Thinking: Dispatch.")
        mock_gemini.add_expected_call("escalate", {"reason": "System crash", "failure_class": "SYSTEM_CRASH"}, text="Thinking: Escalating.")

        result = bag.start_job(objective="Crash test.")
        assert "pending_escalation" in result
        esc = result["pending_escalation"]
        assert esc["signal"] == "NEED_INTERVENTION"
        assert esc["error_detail"]["failure_class"] == "SYSTEM_CRASH"

    def test_start_job_with_hold_for_human(self, mock_gemini):
        bag = ClawBag(name="test_bag")
        bag.manager.register_node(hold_node)

        delivered: list[dict] = []  # type: ignore[type-arg]

        def handler(tid: str, req: dict) -> None:  # type: ignore[type-arg]
            delivered.append(req)

        bag.register_hitl_handler(handler)
        
        mock_gemini.add_expected_call("dispatch_node", {"node_id": "hold_node"}, text="Thinking: Dispatch.")
        mock_gemini.add_expected_call("suspend", {"human_request_message": "Needs human look."}, text="Thinking: Suspending.")
        
        result = bag.start_job(objective="HITL test.")
        assert result.get("suspended") is True
        assert len(delivered) == 1

    def test_start_job_prerequisite_stall_queues_and_resolves(self, mock_gemini):
        """
        Gap 1 (F-REQ-34 / B-REQ-14): Consumer node with unmet prerequisite is
        placed in STALLED queue. Orchestrator prioritizes producer, executes it,
        then re-evaluates and resolves the consumer.
        """
        bag = ClawBag(name="test_bag")

        @clawnode(id="producer_node", description="Produces a document.", bag="test")
        def producer_node(state: dict) -> ClawOutput:  # type: ignore[type-arg]
            return ClawOutput(
                signal=Signal.DONE,
                node_id="producer_node",
                orchestrator_summary="Produced document.",
                result_uri="uri://producer.json",
            )

        @clawnode(
            id="consumer_node",
            description="Consumes document.",
            bag="test",
            requires=["producer_node_result"],
        )
        def consumer_node(state: dict) -> ClawOutput:  # type: ignore[type-arg]
            return ClawOutput(
                signal=Signal.DONE,
                node_id="consumer_node",
                orchestrator_summary="Consumed document.",
                result_uri="uri://consumer.json",
            )

        # Register consumer first -- forces a naive scheduler to attempt it before producer
        bag.manager.register_node(consumer_node)
        bag.manager.register_node(producer_node)

        mock_gemini.add_expected_call("dispatch_node", {"node_id": "producer_node"}, text="Thinking: Dispatch producer.")
        mock_gemini.add_expected_call("dispatch_node", {"node_id": "consumer_node"}, text="Thinking: Dispatch consumer.")
        mock_gemini.add_expected_call("complete", {"final_summary": "Done."}, text="Thinking: Done.")

        result = bag.start_job(
            objective="Test prerequisite stall and resolution.",
            inputs={},
        )

        assert result is not None

        # 1. Job must not terminate as NEED_INTERVENTION
        output = result.get("current_output") or {}
        assert output.get("signal") != Signal.NEED_INTERVENTION, (
            "Unmet prerequisite should stall the node, not terminate the job"
        )

        # 2. consumer_node must have entered the STALLED queue at some point.
        timeline = result.get("timeline", [])
        stall_events = [
            e
            for e in timeline
            if e.get("node_id") == "consumer_node" and e.get("signal") == "STALLED"
        ]
        assert len(stall_events) >= 1, (
            "consumer_node should have emitted a STALLED event before resolution"
        )

        # 3. A RESOLVING event must follow the producer's DONE signal
        resolving_events = [e for e in timeline if e.get("signal") == "RESOLVING"]
        assert len(resolving_events) >= 1, (
            "Orchestrator must enter RESOLVING state after a DONE signal (F-REQ-34)"
        )

        # 4. Both nodes must have committed results to the archive
        archive = result.get("document_archive", {})
        assert "producer_node_result" in archive
        assert "consumer_node_result" in archive

        # 5. stalled_queue must be empty at job completion
        stalled = result.get("stalled_queue", [])
        assert "consumer_node" not in stalled


# ── ClawBag Repr Tests ───────────────────────────────────────────────────────


class TestClawBagRepr:
    def test_repr_uncompiled(self):
        bag = ClawBag(name="test_bag")
        r = repr(bag)
        assert "test_bag" in r
        assert "uncompiled" in r

    def test_repr_compiled(self):
        bag = ClawBag(name="test_bag")
        bag.manager.register_node(success_node)
        bag.compile_graph()
        r = repr(bag)
        assert "compiled" in r
        assert "dirty" not in r


# ── ClawBag Audit & Rollback Tests ───────────────────────────────────────────


class TestClawBagAuditRollback:
    def test_audit_node_delegates(self):
        bag = ClawBag(name="test_bag")
        bag.manager.register_node(success_node)
        audit = bag.audit_node("success_node")
        assert audit["node_id"] == "success_node"
        assert audit["source"] is not None

    def test_rollback_bag_resets_state(self):
        bag = ClawBag(name="test_bag")
        bag.manager.register_node(success_node)  # v1
        bag.manager.register_node(failing_node)  # v2
        bag.compile_graph()

        assert not bag.is_dirty
        bag.rollback_bag(version=1)
        assert bag.manager.version == 1
        assert "success_node" in bag.manager
        assert "failing_node" not in bag.manager
        # Graph should be dirty after rollback (version mismatch).
        assert bag.is_dirty

    def test_skills_property(self):
        bag = ClawBag(name="test_bag", skills_dir="/tmp/skills")
        assert bag.skills is not None
        assert bag.skills.skills_dir is not None


# ── ClawBag Summary Tests ────────────────────────────────────────────────────


class TestClawBagSummary:
    def test_get_summary_without_timeline(self):
        """Fallback: summary generated from SignalManager state."""
        bag = ClawBag(name="test_bag")
        # Force fallback by removing the default timeline
        bag.signal_manager._timeline = None
        bag.manager.register_node(success_node)
        output = ClawOutput(
            signal=Signal.DONE,
            node_id="success_node",
            orchestrator_summary="Task completed.",
            result_uri="uri://test",
        )
        bag.signal_manager.process_signal(output)
        summary = bag.get_summary("any_thread")
        assert "success_node" in summary

    def test_get_summary_with_timeline(self):
        """With TimelineBuffer, get_summary reads from durable events."""
        from clawgraph.core.timeline import TimelineBuffer

        timeline = TimelineBuffer()
        bag = ClawBag(name="test_bag")
        bag.signal_manager._timeline = timeline

        output = ClawOutput(
            signal=Signal.DONE,
            node_id="success_node",
            orchestrator_summary="Phase 1 done.",
            result_uri="uri://test",
        )
        bag.signal_manager.set_active_thread("thread_1")
        bag.signal_manager.process_signal(output)

        summary = bag.get_summary("thread_1")
        assert "Phase 1 done" in summary
        assert "success_node" in summary
