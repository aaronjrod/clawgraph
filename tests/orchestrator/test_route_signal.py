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
    def test_done_routes_to_complete_only_if_orchestrator(self):
        # In the new model, only signals from the "orchestrator" node ID are terminal.
        # Signals from worker nodes (even DONE) route back to the orchestrator (via dispatch_node).
        state: BagState = {  # type: ignore[typeddict-item]
            "current_node_id": "orchestrator",
            "current_output": {"signal": Signal.DONE, "node_id": "orchestrator"},
        }
        assert route_signal(state) == ROUTE_COMPLETE

    def test_worker_done_routes_to_dispatch(self):
        state: BagState = {  # type: ignore[typeddict-item]
            "current_node_id": "worker",
            "current_output": {"signal": Signal.DONE, "node_id": "worker"},
        }
        assert route_signal(state) == ROUTE_NEXT_NODE

    def test_failed_routes_to_escalate_only_if_orchestrator(self):
        state: BagState = {  # type: ignore[typeddict-item]
            "current_node_id": "orchestrator",
            "current_output": {"signal": Signal.FAILED, "node_id": "orchestrator"},
        }
        assert route_signal(state) == ROUTE_ESCALATE

    def test_hold_for_human_routes_to_suspend_only_if_orchestrator(self):
        state: BagState = {  # type: ignore[typeddict-item]
            "current_node_id": "orchestrator",
            "current_output": {"signal": Signal.HOLD_FOR_HUMAN, "node_id": "orchestrator"},
        }
        assert route_signal(state) == ROUTE_SUSPEND

    def test_worker_signals_always_route_to_dispatch(self):
        # All signals from worker nodes must go back to the orchestrator to be processed.
        signals = [Signal.FAILED, Signal.NEED_INTERVENTION, Signal.HOLD_FOR_HUMAN, Signal.NEED_INFO]
        for s in signals:
            state: BagState = {  # type: ignore[typeddict-item]
                "current_node_id": "worker",
                "current_output": {"signal": s, "node_id": "worker"},
            }
            assert route_signal(state) == ROUTE_NEXT_NODE
