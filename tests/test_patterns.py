"""Tests for clawgraph.bag.patterns — DocumentNode, VerificationNode, AggregatorBuilder."""

from clawgraph.bag.patterns import (
    AggregatorBuilder,
    CheckResult,
    DocumentEdit,
    DocumentNode,
    VerificationNode,
)
from clawgraph.core.models import ClawOutput, FailureClass, Signal

# ── DocumentNode ─────────────────────────────────────────────────────────────


class TestDocumentNode:
    def test_create(self):
        dn = DocumentNode(node_id="editor")
        result = dn.create(uri="uri://doc_v1.md", summary="Drafted v1.")
        assert isinstance(result, ClawOutput)
        assert result.signal == Signal.DONE
        assert "Created" in result.orchestrator_summary
        assert result.result_uri == "uri://doc_v1.md"

    def test_read(self):
        dn = DocumentNode(node_id="reader")
        result = dn.read(
            finding="Stability mismatch in Section 4.2.",
            uri="uri://doc_v1.md",
        )
        assert result.signal == Signal.DONE
        assert "Found" in result.orchestrator_summary
        assert "Stability mismatch" in result.orchestrator_summary

    def test_update_precision_edits(self):
        dn = DocumentNode(node_id="editor")
        edits = [
            DocumentEdit(
                section="Section 3",
                old_content="old impurities",
                new_content="new impurities",
                reason="Updated per latest spec",
            ),
            DocumentEdit(
                section="L45-60",
                new_content="new table data",
                reason="Table refresh",
            ),
        ]
        result = dn.update(
            uri="uri://doc_v2.md",
            edits=edits,
            summary="Updated impurities table.",
        )
        assert result.signal == Signal.DONE
        assert "2 edits" in result.orchestrator_summary
        assert "Section 3" in result.orchestrator_summary

    def test_rewrite(self):
        dn = DocumentNode(node_id="editor")
        result = dn.rewrite(
            uri="uri://doc_v3.md",
            summary="Complete CCDS restructuring.",
        )
        assert result.signal == Signal.DONE
        assert "Rewrote" in result.orchestrator_summary


# ── VerificationNode ─────────────────────────────────────────────────────────


class TestVerificationNode:
    def test_all_pass(self):
        vn = VerificationNode(node_id="verifier")
        checks = [
            CheckResult(name="syntax", passed=True),
            CheckResult(name="tests", passed=True),
        ]
        result = vn.evaluate(checks=checks, artifact_uri="uri://module.py")
        assert result.signal == Signal.DONE
        assert "2 checks passed" in result.orchestrator_summary

    def test_some_failures(self):
        vn = VerificationNode(node_id="verifier")
        checks = [
            CheckResult(name="syntax", passed=True),
            CheckResult(
                name="tests",
                passed=False,
                expected="0 failures",
                actual="3 failures",
                message="3 tests failed",
            ),
        ]
        result = vn.evaluate(checks=checks, artifact_uri="uri://module.py")
        assert result.signal == Signal.FAILED
        assert result.error_detail is not None
        assert result.error_detail.failure_class == FailureClass.LOGIC_ERROR
        assert result.error_detail.expected == "0 failures"
        assert result.error_detail.actual == "3 failures"
        assert "1/2 checks failed" in result.orchestrator_summary

    def test_all_failures(self):
        vn = VerificationNode(node_id="verifier")
        checks = [
            CheckResult(name="lint", passed=False, message="lint errors found"),
            CheckResult(name="types", passed=False, message="type errors found"),
        ]
        result = vn.evaluate(checks=checks, artifact_uri="uri://module.py")
        assert result.signal == Signal.FAILED
        assert "2/2 checks failed" in result.orchestrator_summary

    def test_empty_checks(self):
        vn = VerificationNode(node_id="verifier")
        result = vn.evaluate(checks=[], artifact_uri="uri://module.py")
        assert result.signal == Signal.DONE
        assert "0 checks passed" in result.orchestrator_summary


# ── AggregatorBuilder ────────────────────────────────────────────────────────


def _branch_done(state: dict) -> ClawOutput:
    return ClawOutput(
        signal=Signal.DONE,
        node_id="branch_ok",
        orchestrator_summary="Branch passed.",
        result_uri="uri://branch_ok.json",
    )


def _branch_failed(state: dict) -> ClawOutput:
    from clawgraph.core.models import ErrorDetail, FailureClass
    return ClawOutput(
        signal=Signal.FAILED,
        node_id="branch_fail",
        orchestrator_summary="Branch failed.",
        error_detail=ErrorDetail(
            failure_class=FailureClass.LOGIC_ERROR,
            message="test failure",
        ),
    )


def _branch_crash(state: dict) -> ClawOutput:
    raise RuntimeError("Unexpected crash!")


class TestAggregatorBuilder:
    def test_all_done(self):
        ab = AggregatorBuilder(aggregator_id="agg")
        ab.add_branch("b1", "node_a", _branch_done)
        ab.add_branch("b2", "node_b", _branch_done)
        result = ab.run()

        assert result.output.signal == Signal.DONE
        assert len(result.output.branch_breakdown) == 2
        assert len(result.branch_outputs) == 2
        assert "2 branches completed" in result.output.orchestrator_summary

    def test_all_failed(self):
        ab = AggregatorBuilder(aggregator_id="agg")
        ab.add_branch("b1", "node_a", _branch_failed)
        ab.add_branch("b2", "node_b", _branch_failed)
        result = ab.run()

        assert result.output.signal == Signal.FAILED
        assert result.output.error_detail is not None

    def test_mixed_partial(self):
        ab = AggregatorBuilder(aggregator_id="agg")
        ab.add_branch("b1", "node_a", _branch_done)
        ab.add_branch("b2", "node_b", _branch_failed)
        result = ab.run()

        assert result.output.signal == Signal.PARTIAL
        assert result.output.result_uri is not None
        assert "1/2 passed" in result.output.orchestrator_summary

    def test_crash_synthesized(self):
        ab = AggregatorBuilder(aggregator_id="agg")
        ab.add_branch("b1", "node_a", _branch_done)
        ab.add_branch("b2", "node_crash", _branch_crash)
        result = ab.run()

        assert result.output.signal == Signal.PARTIAL
        crash_branch = next(
            br for br in result.output.branch_breakdown
            if br.branch_id == "b2"
        )
        assert crash_branch.signal == Signal.FAILED
        assert crash_branch.error_detail is not None
        assert crash_branch.error_detail.failure_class == FailureClass.SYSTEM_CRASH

    def test_partial_commit_policy(self):
        ab = AggregatorBuilder(aggregator_id="agg", partial_commit_policy="atomic")
        ab.add_branch("b1", "node_a", _branch_done)
        result = ab.run()
        assert result.output.partial_commit_policy == "atomic"

    def test_branch_breakdown_populated(self):
        ab = AggregatorBuilder(aggregator_id="agg")
        ab.add_branch("lint", "lint_check", _branch_done)
        ab.add_branch("tests", "test_runner", _branch_failed)
        result = ab.run()

        breakdown = {br.branch_id: br for br in result.output.branch_breakdown}
        assert "lint" in breakdown
        assert "tests" in breakdown
        assert breakdown["lint"].signal == Signal.DONE
        assert breakdown["tests"].signal == Signal.FAILED
