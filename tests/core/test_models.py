"""Tests for clawgraph.core.models — Pydantic schema validation."""

import pytest
from pydantic import ValidationError

from clawgraph.core.models import (
    AggregatorOutput,
    BranchResult,
    ClawOutput,
    ErrorDetail,
    FailureClass,
    HumanRequest,
    InfoRequest,
    Signal,
)

# ── Signal Enum ────────────────────────────────────────────────────────────────


class TestSignalEnum:
    def test_all_signals_exist(self):
        assert len(Signal) == 6
        expected = {"DONE", "FAILED", "PARTIAL", "NEED_INFO", "HOLD_FOR_HUMAN", "NEED_INTERVENTION"}
        assert {s.value for s in Signal} == expected

    def test_signal_is_str_enum(self):
        assert Signal.DONE == "DONE"
        assert isinstance(Signal.DONE, str)


class TestFailureClassEnum:
    def test_all_classes_exist(self):
        assert len(FailureClass) == 5
        expected = {
            "LOGIC_ERROR",
            "SCHEMA_MISMATCH",
            "TOOL_FAILURE",
            "GUARDRAIL_VIOLATION",
            "SYSTEM_CRASH",
        }
        assert {f.value for f in FailureClass} == expected


# ── ClawOutput Valid Construction ──────────────────────────────────────────────


class TestClawOutputValid:
    def test_done_signal(self):
        out = ClawOutput(
            signal=Signal.DONE,
            node_id="test_node",
            orchestrator_summary="Task completed.",
            result_uri="s3://bucket/result.json",
        )
        assert out.signal == Signal.DONE
        assert out.result_uri == "s3://bucket/result.json"
        assert out.schema_version == 1
        assert out.output_id  # auto-generated UUID

    def test_failed_signal(self):
        out = ClawOutput(
            signal=Signal.FAILED,
            node_id="test_node",
            orchestrator_summary="Logic error in processing.",
            error_detail=ErrorDetail(
                failure_class=FailureClass.LOGIC_ERROR,
                message="Expected numeric, got string.",
            ),
        )
        assert out.signal == Signal.FAILED
        assert out.error_detail.failure_class == FailureClass.LOGIC_ERROR

    def test_partial_signal(self):
        out = ClawOutput(
            signal=Signal.PARTIAL,
            node_id="aggregator_1",
            orchestrator_summary="3 of 5 branches passed.",
            result_uri="s3://bucket/partial.json",
            error_detail=ErrorDetail(
                failure_class=FailureClass.TOOL_FAILURE,
                message="2 branches failed.",
            ),
        )
        assert out.signal == Signal.PARTIAL

    def test_need_info_signal(self):
        out = ClawOutput(
            signal=Signal.NEED_INFO,
            node_id="research_node",
            orchestrator_summary="Need clarification on target audience.",
            info_request=InfoRequest(
                question="Who is the target audience?",
                context="Document mentions multiple segments.",
            ),
        )
        assert out.info_request.target == "SO"

    def test_hold_for_human_signal(self):
        out = ClawOutput(
            signal=Signal.HOLD_FOR_HUMAN,
            node_id="deploy_node",
            orchestrator_summary="Awaiting deployment approval.",
            human_request=HumanRequest(
                message="Approve deployment of v2.1 to production?",
                action_type="approve_deploy",
            ),
        )
        assert out.human_request.action_type == "approve_deploy"

    def test_need_intervention_signal(self):
        out = ClawOutput(
            signal=Signal.NEED_INTERVENTION,
            node_id="monitor_node",
            orchestrator_summary="Schema drift detected.",
            error_detail=ErrorDetail(
                failure_class=FailureClass.SCHEMA_MISMATCH,
                message="Expected field 'status' not found in response.",
                expected="status: str",
                actual="field missing",
            ),
        )
        assert out.error_detail.expected == "status: str"

    def test_output_id_unique(self):
        out1 = ClawOutput(
            signal=Signal.DONE,
            node_id="n1",
            orchestrator_summary="Done.",
            result_uri="uri://1",
        )
        out2 = ClawOutput(
            signal=Signal.DONE,
            node_id="n2",
            orchestrator_summary="Done.",
            result_uri="uri://2",
        )
        assert out1.output_id != out2.output_id

    def test_optional_fields_default_none(self):
        out = ClawOutput(
            signal=Signal.DONE,
            node_id="n",
            orchestrator_summary="Done.",
            result_uri="uri://x",
        )
        assert out.operator_summary is None
        assert out.audit_hint is None
        assert out.continuation_context is None
        assert out.started_at is None
        assert out.completed_at is None
        assert out.orchestrator_synthesized is False


# ── ClawOutput Validator Enforcement ───────────────────────────────────────────


class TestClawOutputValidators:
    def test_done_requires_result_uri(self):
        with pytest.raises(ValidationError, match="DONE signal requires result_uri"):
            ClawOutput(
                signal=Signal.DONE,
                node_id="n",
                orchestrator_summary="Done.",
                # Missing result_uri
            )

    def test_failed_requires_error_detail(self):
        with pytest.raises(ValidationError, match="FAILED signal requires error_detail"):
            ClawOutput(
                signal=Signal.FAILED,
                node_id="n",
                orchestrator_summary="Failed.",
                # Missing error_detail
            )

    def test_partial_requires_result_uri(self):
        with pytest.raises(ValidationError, match="PARTIAL signal requires result_uri"):
            ClawOutput(
                signal=Signal.PARTIAL,
                node_id="n",
                orchestrator_summary="Partial.",
                # Missing result_uri
                error_detail=ErrorDetail(failure_class=FailureClass.LOGIC_ERROR, message="foo"),
            )

    def test_partial_requires_error_detail(self):
        with pytest.raises(ValidationError, match="PARTIAL signal requires error_detail"):
            ClawOutput(
                signal=Signal.PARTIAL,
                node_id="n",
                orchestrator_summary="Partial.",
                result_uri="uri://partial",
                # Missing error_detail
            )

    def test_need_info_requires_info_request(self):
        with pytest.raises(ValidationError, match="NEED_INFO signal requires info_request"):
            ClawOutput(
                signal=Signal.NEED_INFO,
                node_id="n",
                orchestrator_summary="Need info.",
                # Missing info_request
            )

    def test_hold_for_human_requires_human_request(self):
        with pytest.raises(ValidationError, match="HOLD_FOR_HUMAN signal requires human_request"):
            ClawOutput(
                signal=Signal.HOLD_FOR_HUMAN,
                node_id="n",
                orchestrator_summary="Need human.",
                # Missing human_request
            )

    def test_need_intervention_requires_error_detail(self):
        with pytest.raises(ValidationError, match="NEED_INTERVENTION signal requires error_detail"):
            ClawOutput(
                signal=Signal.NEED_INTERVENTION,
                node_id="n",
                orchestrator_summary="Drift.",
                # Missing error_detail
            )


# ── AggregatorOutput ──────────────────────────────────────────────────────────


class TestAggregatorOutput:
    def test_valid_aggregator(self):
        out = AggregatorOutput(
            signal=Signal.DONE,
            node_id="agg_1",
            orchestrator_summary="All branches passed.",
            result_uri="s3://merged.json",
            branch_breakdown=[
                BranchResult(
                    branch_id="b1",
                    node_id="worker_1",
                    signal=Signal.DONE,
                    summary="Branch 1 OK.",
                    result_uri="s3://b1.json",
                ),
            ],
        )
        assert len(out.branch_breakdown) == 1
        assert out.partial_commit_policy == "eager"

    def test_aggregator_requires_branches(self):
        with pytest.raises(ValidationError, match="at least one BranchResult"):
            AggregatorOutput(
                signal=Signal.DONE,
                node_id="agg_1",
                orchestrator_summary="Done.",
                result_uri="s3://merged.json",
                branch_breakdown=[],  # Empty!
            )

    def test_aggregator_with_partial(self):
        out = AggregatorOutput(
            signal=Signal.PARTIAL,
            node_id="agg_1",
            orchestrator_summary="2 of 3 passed.",
            result_uri="s3://partial.json",
            error_detail=ErrorDetail(
                failure_class=FailureClass.LOGIC_ERROR,
                message="1 branch failed.",
            ),
            branch_breakdown=[
                BranchResult(branch_id="b1", node_id="w1", signal=Signal.DONE, summary="OK."),
                BranchResult(
                    branch_id="b2",
                    node_id="w2",
                    signal=Signal.FAILED,
                    summary="Failed.",
                    error_detail=ErrorDetail(
                        failure_class=FailureClass.TOOL_FAILURE,
                        message="API timeout.",
                    ),
                ),
            ],
        )
        assert out.signal == Signal.PARTIAL
        assert len(out.branch_breakdown) == 2
