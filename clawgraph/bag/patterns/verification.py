"""Verification node pattern -- test/validation helpers.

Spec ref: 06_patterns.md S3.4
"""

from __future__ import annotations

from dataclasses import dataclass

from clawgraph.core.models import (
    ClawOutput,
    ErrorDetail,
    FailureClass,
    Signal,
)


@dataclass
class CheckResult:
    """Result of a single verification check."""

    name: str
    passed: bool
    expected: str = ""
    actual: str = ""
    message: str = ""


class VerificationNode:
    """Helpers for test/validation nodes (Part 3.4).

    Runs checks against an artifact and auto-populates error_detail on failure.

    Usage::

        vn = VerificationNode(node_id="verify_output")
        checks = [
            CheckResult(name="syntax", passed=True),
            CheckResult(name="tests", passed=False, expected="0 failures", actual="3 failures"),
        ]
        return vn.evaluate(checks=checks, artifact_uri="uri://module.py")
    """

    def __init__(self, node_id: str) -> None:
        self.node_id = node_id

    def evaluate(
        self,
        checks: list[CheckResult],
        artifact_uri: str,
    ) -> ClawOutput:
        """Run all checks and return DONE or FAILED with structured detail."""
        failures = [c for c in checks if not c.passed]
        total = len(checks)

        if not failures:
            return ClawOutput(
                signal=Signal.DONE,
                node_id=self.node_id,
                orchestrator_summary=f"All {total} checks passed.",
                result_uri=artifact_uri,
            )

        # Build failure detail from the first failure, with full summary.
        first = failures[0]
        return ClawOutput(
            signal=Signal.FAILED,
            node_id=self.node_id,
            orchestrator_summary=(
                f"Verification failed: {len(failures)}/{total} checks failed. "
                f"First failure: {first.name}."
            ),
            result_uri=artifact_uri,
            error_detail=ErrorDetail(
                failure_class=FailureClass.LOGIC_ERROR,
                message="; ".join(
                    f"{f.name}: {f.message or 'failed'}" for f in failures
                ),
                expected=first.expected or None,
                actual=first.actual or None,
            ),
        )
