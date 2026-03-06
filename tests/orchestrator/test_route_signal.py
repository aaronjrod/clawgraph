"""Tests for route_signal conditional edge logic."""

from clawgraph.core.models import Signal
from clawgraph.orchestrator.graph import BagState
from clawgraph.orchestrator.hub import (
    ROUTE_COMPLETE,
    ROUTE_ESCALATE,
    ROUTE_NEXT_NODE,
    ROUTE_SUSPEND,
    route_signal,
)


class TestRouteSignal:
    def test_done_routes_to_complete(self):
        state: BagState = {  # type: ignore[typeddict-item]
            "current_output": {"signal": Signal.DONE},
            "iteration_count": 1,
            "max_iterations": 10,
            "ready_queue": [],
        }
        assert route_signal(state) == ROUTE_COMPLETE

    def test_done_routes_to_next_node_when_queue_nonempty(self):
        state: BagState = {  # type: ignore[typeddict-item]
            "current_output": {"signal": Signal.DONE},
            "iteration_count": 1,
            "max_iterations": 10,
            "ready_queue": ["another_node"],
        }
        assert route_signal(state) == ROUTE_NEXT_NODE

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
            # Retries exhausted -> should escalate.
            "need_info_tracking": {"info_node": {"retries": 3, "max_retries": 3}},
        }
        assert route_signal(state) == ROUTE_ESCALATE

    def test_need_info_within_budget_routes_to_next(self):
        state: BagState = {  # type: ignore[typeddict-item]
            "current_output": {"signal": Signal.NEED_INFO, "node_id": "info_node"},
            "iteration_count": 1,
            "max_iterations": 10,
            "need_info_tracking": {"info_node": {"retries": 0, "max_retries": 3}},
        }
        assert route_signal(state) == ROUTE_NEXT_NODE

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
            "ready_queue": ["some_node"],
        }
        assert route_signal(state) == ROUTE_NEXT_NODE

    def test_budget_exhausted_routes_to_escalate(self):
        state: BagState = {  # type: ignore[typeddict-item]
            "current_output": {"signal": Signal.DONE},
            "iteration_count": 10,
            "max_iterations": 10,
        }
        assert route_signal(state) == ROUTE_ESCALATE
