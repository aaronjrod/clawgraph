"""Shared test fixtures for orchestrator tests.

Decorated ClawNode fixtures used across multiple test modules.
"""

from clawgraph.bag.node import clawnode
from clawgraph.core.models import (
    ClawOutput,
    ErrorDetail,
    FailureClass,
    HumanRequest,
    InfoRequest,
    Signal,
)


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
