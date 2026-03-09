"""TDD tests for GUARDRAIL_VIOLATION signals.

When a node emits a FAILED or PARTIAL signal with a GUARDRAIL_VIOLATION
failure class, the Orchestrator should escalate it to the Super-Orchestrator
for review or remediation.
"""

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
from clawgraph.orchestrator.graph import ClawBag


class TestGuardrailViolation:
    """Nodes emitting GUARDRAIL_VIOLATION should be escalated."""

    def test_direct_guardrail_violation_escalates(self, mock_gemini):
        """A FAILED signal with GUARDRAIL_VIOLATION should escalate."""
        bag = ClawBag(name="guardrail_bag")

        @clawnode(id="rogue_node", description="Attempts a blocked action.", bag="guardrail_bag")
        def rogue_node(state: dict) -> ClawOutput:  # type: ignore[type-arg]
            return ClawOutput(
                signal=Signal.FAILED,
                node_id="rogue_node",
                orchestrator_summary="Action blocked by policy.",
                error_detail=ErrorDetail(
                    failure_class=FailureClass.GUARDRAIL_VIOLATION,
                    message="Attempted to access forbidden directory /etc/shadow.",
                ),
            )

        bag.manager.register_node(rogue_node)
        
        # 1. Dispatch node
        # 2. Node returns FAILED with GUARDRAIL_VIOLATION
        # 3. Orchestrator escalates
        mock_gemini.add_expected_call("dispatch_node", {"node_id": "rogue_node"}, text="Thinking: Dispatching node.")
        mock_gemini.add_expected_call("escalate", {"reason": "Guardrail violation detected.", "failure_class": "GUARDRAIL_VIOLATION"}, text="Thinking: Node violated security policy. Escalating immediately.")

        result = bag.start_job(objective="Test guardrails.", max_iterations=5)

        # The pending escalation should be set
        escalation = result.get("pending_escalation")
        assert escalation is not None
        assert escalation.get("signal") == "NEED_INTERVENTION"
        assert escalation.get("error_detail", {}).get("failure_class") == FailureClass.GUARDRAIL_VIOLATION.value

    def test_partial_guardrail_violation_escalates(self, mock_gemini):
        """A PARTIAL signal containing a GUARDRAIL_VIOLATION branch should escalate."""
        bag = ClawBag(name="guardrail_partial_bag")

        @clawnode(id="agg_node", description="Aggregates parallel work.", bag="guardrail_partial_bag")
        def agg_node(state: dict) -> ClawOutput:  # type: ignore[type-arg]
            return AggregatorOutput(
                signal=Signal.PARTIAL,
                node_id="agg_node",
                orchestrator_summary="Partial success, but one branch hit a guardrail.",
                result_uri="uri://partial.json",
                partial_commit_policy="eager",
                error_detail=ErrorDetail(
                    failure_class=FailureClass.GUARDRAIL_VIOLATION,
                    message="A branch action was blocked by policy.",
                ),
                branch_breakdown=[
                    BranchResult(
                        branch_id="safe_task",
                        node_id="safe_node",
                        signal=Signal.DONE,
                        summary="Safe task completed.",
                        result_uri="uri://safe.json",
                    ),
                    BranchResult(
                        branch_id="unsafe_task",
                        node_id="rogue_node",
                        signal=Signal.FAILED,
                        summary="Unsafe task blocked.",
                        error_detail=ErrorDetail(
                            failure_class=FailureClass.GUARDRAIL_VIOLATION,
                            message="Attempted unauthorized network call.",
                        ),
                    ),
                ],
            )

        bag.manager.register_node(agg_node)
        
        # 1. Dispatch aggregator
        # 2. Returns PARTIAL with GUARDRAIL_VIOLATION in breakdown
        # 3. Orchestrator escalates based on the partial signal's error class
        mock_gemini.add_expected_call("dispatch_node", {"node_id": "agg_node"}, text="Thinking: Dispatching aggregator.")
        mock_gemini.add_expected_call("escalate", {"reason": "Partial aggregation with guardrail violation.", "failure_class": "GUARDRAIL_VIOLATION"}, text="Thinking: A branch violated a guardrail. Escalating partial result.")

        result = bag.start_job(objective="Test partial guardrails.", max_iterations=5)

        # Check eager commit occurred for the valid branch
        archive = result.get("document_archive", {})
        assert "safe_task_result" in archive
        
        # Check escalation state
        escalation = result.get("pending_escalation")
        assert escalation is not None
        assert escalation.get("signal") == "NEED_INTERVENTION"
        assert escalation.get("error_detail", {}).get("failure_class") == FailureClass.GUARDRAIL_VIOLATION.value
