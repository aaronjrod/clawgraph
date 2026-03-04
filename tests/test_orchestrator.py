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
            "current_output": {"signal": Signal.NEED_INFO},
            "iteration_count": 1,
            "max_iterations": 10,
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

    def test_start_job_prerequisite_stall(self):
        """Node with unmet prerequisites → STALLED → NEED_INTERVENTION."""
        bag = ClawBag(name="test_bag")
        bag.manager.register_node(prereq_node)

        result = bag.start_job(
            objective="Test prerequisite checking.",
            inputs={},  # No input_doc provided.
        )

        assert result is not None
        output = result.get("current_output", {})
        assert output.get("signal") == Signal.NEED_INTERVENTION
        assert "missing prerequisites" in output.get("orchestrator_summary", "").lower()


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
