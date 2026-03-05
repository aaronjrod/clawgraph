"""Tests for clawgraph.orchestrator — ClawBag, hub logic, and graph execution."""


from clawgraph.bag.node import clawnode
from clawgraph.core.models import (
    ClawOutput,
    ErrorDetail,
    FailureClass,
    HumanRequest,
    InfoRequest,
    Signal,
)
from clawgraph.orchestrator.graph import BagState, ClawBag
from clawgraph.orchestrator.hub import (
    ROUTE_COMPLETE,
    ROUTE_ESCALATE,
    ROUTE_NEXT_NODE,
    ROUTE_SUSPEND,
    route_signal,
)

# ── Test Fixtures (Decorated Nodes) ───────────────────────────────────────────


@clawnode(
    id="success_node",
    description="Always succeeds.",
    bag="test",
)
def success_node(state: dict) -> ClawOutput:  # type: ignore[type-arg]
    return ClawOutput(
        signal=Signal.DONE,
        node_id="success_node",
        orchestrator_summary="Successfully completed.",
        result_uri="uri://success.json",
    )


@clawnode(
    id="failing_node",
    description="Always fails.",
    bag="test",
)
def failing_node(state: dict) -> ClawOutput:  # type: ignore[type-arg]
    return ClawOutput(
        signal=Signal.FAILED,
        node_id="failing_node",
        orchestrator_summary="Failed intentionally.",
        error_detail=ErrorDetail(
            failure_class=FailureClass.LOGIC_ERROR,
            message="Intentional failure for testing.",
        ),
    )


@clawnode(
    id="crashing_node",
    description="Raises an unhandled exception.",
    bag="test",
)
def crashing_node(state: dict) -> ClawOutput:  # type: ignore[type-arg]
    msg = "Unhandled exception!"
    raise RuntimeError(msg)


@clawnode(
    id="need_info_node",
    description="Requests info.",
    bag="test",
)
def need_info_node(state: dict) -> ClawOutput:  # type: ignore[type-arg]
    return ClawOutput(
        signal=Signal.NEED_INFO,
        node_id="need_info_node",
        orchestrator_summary="Need clarification.",
        info_request=InfoRequest(
            question="What format?",
            context="Output format unclear.",
        ),
    )


@clawnode(
    id="hold_node",
    description="Requests human approval.",
    bag="test",
)
def hold_node(state: dict) -> ClawOutput:  # type: ignore[type-arg]
    return ClawOutput(
        signal=Signal.HOLD_FOR_HUMAN,
        node_id="hold_node",
        orchestrator_summary="Awaiting human approval.",
        human_request=HumanRequest(
            message="Approve deployment?",
            action_type="approve_deploy",
        ),
    )


@clawnode(
    id="prereq_node",
    description="Has prerequisites.",
    bag="test",
    requires=["input_doc"],
)
def prereq_node(state: dict) -> ClawOutput:  # type: ignore[type-arg]
    return ClawOutput(
        signal=Signal.DONE,
        node_id="prereq_node",
        orchestrator_summary="Completed with prereqs.",
        result_uri="uri://prereq_result.json",
    )


# ── Route Signal Tests ────────────────────────────────────────────────────────


class TestRouteSignal:
    def test_done_routes_to_complete(self):
        state: BagState = {  # type: ignore[typeddict-item]
            "current_output": {"signal": Signal.DONE},
            "iteration_count": 1,
            "max_iterations": 10,
        }
        assert route_signal(state) == ROUTE_COMPLETE

    def test_failed_routes_to_escalate(self):
        state: BagState = {  # type: ignore[typeddict-item]
            "current_output": {"signal": Signal.FAILED},
            "iteration_count": 1,
            "max_iterations": 10,
        }
        assert route_signal(state) == ROUTE_ESCALATE

    def test_need_info_routes_to_escalate(self):
        state: BagState = {  # type: ignore[typeddict-item]
            "current_output": {"signal": Signal.NEED_INFO, "node_id": "info_node"},
            "iteration_count": 1,
            "max_iterations": 10,
            # Retries exhausted → should escalate.
            "need_info_tracking": {"info_node": {"retries": 3, "max_retries": 3}},
        }
        assert route_signal(state) == ROUTE_ESCALATE

    def test_hold_for_human_routes_to_suspend(self):
        state: BagState = {  # type: ignore[typeddict-item]
            "current_output": {"signal": Signal.HOLD_FOR_HUMAN},
            "iteration_count": 1,
            "max_iterations": 10,
        }
        assert route_signal(state) == ROUTE_SUSPEND

    def test_need_intervention_routes_to_escalate(self):
        state: BagState = {  # type: ignore[typeddict-item]
            "current_output": {"signal": Signal.NEED_INTERVENTION},
            "iteration_count": 1,
            "max_iterations": 10,
        }
        assert route_signal(state) == ROUTE_ESCALATE

    def test_no_signal_routes_to_dispatch(self):
        state: BagState = {  # type: ignore[typeddict-item]
            "current_output": {},
            "iteration_count": 0,
            "max_iterations": 10,
            "ready_queue": ["some_node"],  # Must have nodes to dispatch.
        }
        assert route_signal(state) == ROUTE_NEXT_NODE

    def test_budget_exhausted_routes_to_escalate(self):
        state: BagState = {  # type: ignore[typeddict-item]
            "current_output": {},
            "iteration_count": 10,
            "max_iterations": 10,
        }
        assert route_signal(state) == ROUTE_ESCALATE


# ── ClawBag Tests ─────────────────────────────────────────────────────────────


class TestClawBagSetup:
    def test_creation(self):
        bag = ClawBag(name="test_bag")
        assert bag.name == "test_bag"
        assert not bag.is_compiled
        assert bag.is_dirty  # Never compiled.

    def test_register_node_via_manager(self):
        bag = ClawBag(name="test_bag")
        bag.manager.register_node(success_node)
        assert "success_node" in bag.manager
        assert bag.is_dirty  # Not yet compiled.

    def test_hitl_handler_registration(self):
        bag = ClawBag(name="test_bag")
        handler_called = []

        def my_handler(thread_id: str, request: dict) -> None:  # type: ignore[type-arg]
            handler_called.append((thread_id, request))

        bag.register_hitl_handler(my_handler)
        assert bag._hitl_handler is not None


class TestClawBagCompilation:
    def test_compile_graph(self):
        bag = ClawBag(name="test_bag")
        bag.manager.register_node(success_node)
        graph = bag.compile_graph()
        assert graph is not None
        assert bag.is_compiled
        assert not bag.is_dirty

    def test_lazy_compilation_skips_when_clean(self):
        bag = ClawBag(name="test_bag")
        bag.manager.register_node(success_node)
        bag.compile_graph()
        version_after_first = bag._last_compiled_version

        # Compile again — should reuse cached.
        bag.compile_graph_if_dirty()
        assert bag._last_compiled_version == version_after_first

    def test_lazy_compilation_recompiles_when_dirty(self):
        bag = ClawBag(name="test_bag")
        bag.manager.register_node(success_node)
        bag.compile_graph()
        v1 = bag._last_compiled_version

        # Add a node — manifest is now dirty.
        bag.manager.register_node(failing_node)
        assert bag.is_dirty

        bag.compile_graph_if_dirty()
        assert bag._last_compiled_version > v1
        assert not bag.is_dirty


class TestClawBagExecution:
    def test_start_job_success(self):
        bag = ClawBag(name="test_bag")
        bag.manager.register_node(success_node)

        result = bag.start_job(
            objective="Test successful execution.",
            max_iterations=5,
        )

        assert result is not None
        # Manifest should be unlocked after execution.
        assert not bag.manager.locked

    def test_start_job_locks_and_unlocks(self):
        bag = ClawBag(name="test_bag")
        bag.manager.register_node(success_node)

        # Before job.
        assert not bag.manager.locked

        bag.start_job(objective="Test locking.")

        # After job — should be unlocked.
        assert not bag.manager.locked

    def test_start_job_with_failing_node(self):
        bag = ClawBag(name="test_bag")
        bag.manager.register_node(failing_node)

        result = bag.start_job(objective="Test failure handling.")

        assert result is not None
        assert not bag.manager.locked

    def test_start_job_with_crashing_node(self):
        """Exception interception: unhandled exceptions → synthesized FAILED."""
        bag = ClawBag(name="test_bag")
        bag.manager.register_node(crashing_node)

        result = bag.start_job(objective="Test exception interception.")

        assert result is not None
        # Should not raise — the exception is caught and synthesized.
        output = result.get("current_output", {})
        assert output.get("signal") == Signal.FAILED
        assert output.get("orchestrator_synthesized") is True
        assert not bag.manager.locked

    def test_start_job_with_hold_for_human(self):
        bag = ClawBag(name="test_bag")
        bag.manager.register_node(hold_node)

        delivered = []

        def handler(tid: str, req: dict) -> None:  # type: ignore[type-arg]
            delivered.append((tid, req))

        bag.register_hitl_handler(handler)
        result = bag.start_job(objective="Test HITL.")

        assert result.get("suspended") is True
        assert len(delivered) == 1

    def test_start_job_prerequisite_stall_queues_and_resolves(self):
        """
        Gap 1 (F-REQ-34 / B-REQ-14): Consumer node with unmet prerequisite is
        placed in STALLED queue. Orchestrator prioritizes producer, executes it,
        then re-evaluates and resolves the consumer.
        """
        bag = ClawBag(name="test_bag")

        @clawnode(id="producer_node", description="Produces a document.", bag="test")
        def producer_node(state: dict) -> ClawOutput:
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
            requires=["producer_node_result"],  # Must match archive key written by producer
        )
        def consumer_node(state: dict) -> ClawOutput:
            return ClawOutput(
                signal=Signal.DONE,
                node_id="consumer_node",
                orchestrator_summary="Consumed document.",
                result_uri="uri://consumer.json",
            )

        # Register consumer first — forces a naive scheduler to attempt it before producer
        bag.manager.register_node(consumer_node)
        bag.manager.register_node(producer_node)

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
        #    Check the timeline/event log rather than just the final queue state,
        #    since a resolved node should have exited the queue by job end.
        timeline = result.get("timeline", [])
        stall_events = [
            e for e in timeline
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

        # Verify the archive key convention before testing consumer resolution.
        # If this fails, the requires= key on consumer_node is wrong, not the stall logic.
        assert "producer_node_result" in archive, (
            "Archive key convention check: producer_node should write to "
            "'producer_node_result'. If missing, check how result_uri maps to "
            "archive keys — the consumer's requires= field must match exactly."
        )

        assert "consumer_node_result" in archive, (
            "Consumer node was not executed after prerequisite was resolved"
        )

        # 5. stalled_queue must be empty at job completion — consumer was resolved
        stalled = result.get("stalled_queue", [])
        assert "consumer_node" not in stalled, (
            "consumer_node should have been moved out of stalled_queue after resolution"
        )


# ── Audit Gap TDD Tests ───────────────────────────────────────────────────────


class TestGap2HITLContextInjection:
    def test_suspend_node_injects_timeline(self):
        """Gap 2 (F-REQ-32): suspend node should inject timeline events into human_request."""
        from clawgraph.core.models import ClawOutput, Signal
        from clawgraph.core.timeline import TimelineBuffer
        from clawgraph.orchestrator.hub import _make_suspend_node

        delivered = []
        def handler(tid: str, req: dict) -> None:
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

        state: BagState = {
            "current_output": {
                "signal": Signal.HOLD_FOR_HUMAN,
                "human_request": {"message": "approve deployment?"}
            },
            "thread_id": "test_thread"
        }
        suspend(state)

        assert len(delivered) == 1
        # The handler should receive a payload augmented with context.
        assert "timeline_context" in delivered[0]
        assert len(delivered[0]["timeline_context"]) >= 1


class TestGap3EscalationPolicyEnforcement:
    def test_route_signal_respects_need_info_retries(self):
        """Gap 3 (F-REQ-10): NEED_INFO should not escalate until max_retries or ttl is exhausted."""
        state: BagState = {
            "current_output": {"signal": Signal.NEED_INFO, "node_id": "need_info_node"},
            "iteration_count": 1,
            "max_iterations": 10,
            # We expect state tracking for retries
            "need_info_tracking": {"need_info_node": {"retries": 0}}
        }
        # First time shouldn't escalate immediately if policy allows retries
        assert route_signal(state) != ROUTE_ESCALATE


class TestGap4PartialCommitPolicy:
    def test_eager_partial_commit_registers_successes(self):
        """Gap 4 (F-REQ-13): partial_commit_policy='eager' should commit successful branches immediately."""
        from clawgraph.core.models import AggregatorOutput, BranchResult, ErrorDetail, FailureClass

        bag = ClawBag(name="test_bag")

        @clawnode(id="agg_node", description="Aggregates", bag="test")
        def agg_node(state: dict) -> ClawOutput:
            return AggregatorOutput(
                signal=Signal.PARTIAL,
                node_id="agg_node",
                orchestrator_summary="Partial completion",
                result_uri="uri://agg.json",
                partial_commit_policy="eager",
                error_detail=ErrorDetail(failure_class=FailureClass.TOOL_FAILURE, message="Failed."),
                branch_breakdown=[
                    BranchResult(branch_id="b1", node_id="w1", signal=Signal.DONE, summary="OK", result_uri="uri://b1.json")
                ]
            )

        bag.manager.register_node(agg_node)
        result = bag.start_job(objective="Test eager commit")

        archive = result.get("document_archive", {})
        # Because policy is eager, intermediate DONE branches MUST be committed.
        assert "b1_result" in archive, "Eager policy violated: branch result was not committed despite DONE signal."

    def test_atomic_partial_commit_delays_artifact_registration(self):
        """Gap 4 (F-REQ-13): partial_commit_policy='atomic' should delay commit until aggregator completes."""
        from clawgraph.core.models import AggregatorOutput, BranchResult, ErrorDetail, FailureClass

        bag = ClawBag(name="test_bag")

        @clawnode(id="agg_node", description="Aggregates", bag="test")
        def agg_node(state: dict) -> ClawOutput:
            return AggregatorOutput(
                signal=Signal.PARTIAL,
                node_id="agg_node",
                orchestrator_summary="Partial completion",
                result_uri="uri://agg.json",
                partial_commit_policy="atomic",
                error_detail=ErrorDetail(failure_class=FailureClass.TOOL_FAILURE, message="Failed."),
                branch_breakdown=[
                    BranchResult(branch_id="b1", node_id="w1", signal=Signal.DONE, summary="OK", result_uri="uri://b1.json")
                ]
            )

        bag.manager.register_node(agg_node)
        result = bag.start_job(objective="Test atomic commit")

        archive = result.get("document_archive", {})
        # Because policy is atomic, intermediate DONE branches should NOT be committed in the event of a PARTIAL signal.
        assert "b1_result" not in archive, "Atomic policy violated: branch result committed despite PARTIAL signal."


class TestGap5MultiDomainTagVisibility:
    def test_prerequisite_checker_respects_domain_tags(self):
        """Gap 5 (F-REQ-17): Prerequisite resolution should respect multi-bag tagging in document_archive."""
        from clawgraph.orchestrator.hub import _make_dispatch_node

        bag = ClawBag(name="test_bag")

        @clawnode(id="consumer_node", description="Consumes", bag="test", requires=["secure_doc"])
        def consumer_node(state: dict) -> ClawOutput:
            return ClawOutput(signal=Signal.DONE, node_id="consumer_node", orchestrator_summary="OK", result_uri="uri://ok")

        bag.manager.register_node(consumer_node)

        dispatch = _make_dispatch_node(bag_manager=bag.manager, signal_manager=bag.signal_manager)

        # State with a document from another domain, not tagged public for this bag.
        state: BagState = {
            "current_node_id": "consumer_node",
            "document_archive": {
                "secure_doc": {
                    "uri": "s3://secure",
                    "domain": "other_bag",
                    "tags": ["internal"] # not public
                }
            },
            "bag_manifest": bag.manager.manifest.model_dump()
        }

        updates = dispatch(state)
        output = updates.get("current_output", {})

        # It should stall/fail because it cannot see the document.
        # F-REQ-17: Prerequisite resolution MUST fail (or stall)
        assert output.get("signal") != Signal.DONE, (
            "Node executed but should have been blocked by visibility rules."
        )


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


class TestClawBagSummary:
    def test_get_summary_without_timeline(self):
        """Fallback: summary generated from SignalManager state."""
        bag = ClawBag(name="test_bag")
        bag.manager.register_node(success_node)
        # Manually process a signal so there's state.
        from clawgraph.core.models import ClawOutput, Signal
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
        from clawgraph.core.models import ClawOutput, Signal
        from clawgraph.core.timeline import TimelineBuffer

        timeline = TimelineBuffer()
        bag = ClawBag(name="test_bag")
        # Inject a timeline buffer into the signal manager.
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

