"""Reusable node patterns — DocumentNode, VerificationNode, AggregatorBuilder.

These are helper classes and utilities that implement common node archetypes
from 06_patterns.md (Parts 3, 8). They compose with the @clawnode decorator
rather than replacing it.

Spec ref: 06_patterns.md S3.2-3.4, S8.1-8.3
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

from clawgraph.core.models import (
    AggregatorOutput,
    BranchResult,
    ClawOutput,
    ErrorDetail,
    FailureClass,
    Signal,
)

logger = logging.getLogger(__name__)


# ── Document Node Helpers (Part 8) ───────────────────────────────────────────


@dataclass
class DocumentEdit:
    """A precision edit to apply to a document (Part 8, §8.1).

    Instead of full rewrites, agents produce targeted edits — line-level or
    section-level diffs — that a DocumentArchive manager can apply atomically.
    """

    section: str  # Section or line range identifier, e.g., "Section 3" or "L45-60"
    old_content: str | None = None  # What to replace (None = insert)
    new_content: str = ""  # Replacement content
    reason: str = ""  # Why this edit was made


class DocumentNode:
    """Helpers for CRUD document operations (Part 8).

    Enforces the precision-edit pattern: updates return diffs, not full rewrites.
    Use in combination with @clawnode for the function signature.

    Usage::

        dn = DocumentNode(node_id="clinical_editor")

        # CREATE
        return dn.create(uri="uri://protocol_v1.md", summary="Drafted protocol v1.")

        # READ
        return dn.read(finding="Stability mismatch in Section 4.2.",
                       uri="uri://protocol_v1.md")

        # UPDATE (precision edit)
        edits = [DocumentEdit(section="Section 3", old_content="old", new_content="new")]
        return dn.update(uri="uri://protocol_v2.md", edits=edits,
                         summary="Updated impurities table.")

        # REWRITE
        return dn.rewrite(uri="uri://protocol_v2.md",
                          summary="Complete restructuring for global alignment.")
    """

    def __init__(self, node_id: str) -> None:
        self.node_id = node_id

    def create(self, uri: str, summary: str) -> ClawOutput:
        """Phase: CREATE — Draft initial document."""
        return ClawOutput(
            signal=Signal.DONE,
            node_id=self.node_id,
            orchestrator_summary=f"Created: {summary}",
            result_uri=uri,
        )

    def read(self, finding: str, uri: str) -> ClawOutput:
        """Phase: READ — Scan for specific data and report finding."""
        return ClawOutput(
            signal=Signal.DONE,
            node_id=self.node_id,
            orchestrator_summary=f"Found: {finding}",
            result_uri=uri,
        )

    def update(
        self,
        uri: str,
        edits: list[DocumentEdit],
        summary: str,
    ) -> ClawOutput:
        """Phase: UPDATE — Apply precision patches (§8.1).

        Returns a DONE signal with edit metadata. The edits themselves
        are stored externally; the ClawOutput only contains the summary.
        """
        edit_descriptions = [
            f"[{e.section}]: {e.reason or 'Updated'}" for e in edits
        ]
        detail = "; ".join(edit_descriptions)
        return ClawOutput(
            signal=Signal.DONE,
            node_id=self.node_id,
            orchestrator_summary=f"Updated ({len(edits)} edits): {summary}. Edits: {detail}",
            result_uri=uri,
        )

    def rewrite(self, uri: str, summary: str) -> ClawOutput:
        """Phase: REWRITE — Full document restructure (rare)."""
        return ClawOutput(
            signal=Signal.DONE,
            node_id=self.node_id,
            orchestrator_summary=f"Rewrote: {summary}",
            result_uri=uri,
        )


# ── Verification Node Helpers (Part 3.4) ─────────────────────────────────────


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


# ── Aggregator Builder (Part 3.4) ────────────────────────────────────────────


@dataclass
class BranchSpec:
    """Defines a branch within a fan-out subgraph."""

    branch_id: str
    node_id: str
    fn: Callable[..., ClawOutput]


@dataclass
class AggregationResult:
    """Result of running and aggregating parallel branches."""

    output: AggregatorOutput
    branch_outputs: list[ClawOutput] = field(default_factory=list)


class AggregatorBuilder:
    """Utility for constructing fan-in/fan-out workflows (Part 3.4).

    Runs branch functions, collects their ClawOutputs, and produces a
    single AggregatorOutput with merge semantics:
    - All DONE → DONE
    - Any FAILED (with some DONE) → PARTIAL
    - All FAILED → FAILED

    Usage::

        builder = AggregatorBuilder(
            aggregator_id="quality_gate",
            partial_commit_policy="eager",
        )
        builder.add_branch("lint", "lint_check", lint_fn)
        builder.add_branch("tests", "run_tests", test_fn)
        result = builder.run(state={})
        return result.output  # AggregatorOutput
    """

    def __init__(
        self,
        aggregator_id: str,
        partial_commit_policy: str = "eager",
    ) -> None:
        self.aggregator_id = aggregator_id
        self.partial_commit_policy = partial_commit_policy
        self._branches: list[BranchSpec] = []

    def add_branch(
        self,
        branch_id: str,
        node_id: str,
        fn: Callable[..., ClawOutput],
    ) -> None:
        """Register a branch function to run in the fan-out."""
        self._branches.append(BranchSpec(
            branch_id=branch_id,
            node_id=node_id,
            fn=fn,
        ))

    def run(self, state: dict[str, Any] | None = None) -> AggregationResult:
        """Execute all branches and aggregate into a single AggregatorOutput.

        Branches are run sequentially (parallelism is a runtime concern).
        The merge semantics follow Part 3.4 of the patterns doc.
        """
        state = state or {}
        branch_outputs: list[ClawOutput] = []
        branch_results: list[BranchResult] = []

        for spec in self._branches:
            try:
                output = spec.fn(state)
            except Exception as exc:
                # Synthesize a FAILED output for crashing branches.
                output = ClawOutput(
                    signal=Signal.FAILED,
                    node_id=spec.node_id,
                    orchestrator_summary=f"Branch '{spec.branch_id}' crashed: {exc}",
                    error_detail=ErrorDetail(
                        failure_class=FailureClass.SYSTEM_CRASH,
                        message=str(exc),
                    ),
                    orchestrator_synthesized=True,
                )

            branch_outputs.append(output)
            branch_results.append(BranchResult(
                branch_id=spec.branch_id,
                node_id=spec.node_id,
                signal=output.signal,
                summary=output.orchestrator_summary,
                result_uri=output.result_uri,
                error_detail=output.error_detail,
            ))

        # Merge semantics.
        done_count = sum(1 for o in branch_outputs if o.signal == Signal.DONE)
        fail_count = sum(1 for o in branch_outputs if o.signal in (Signal.FAILED, Signal.NEED_INTERVENTION))
        total = len(branch_outputs)

        if done_count == total:
            # All passed.
            merged_signal = Signal.DONE
            summary = f"All {total} branches completed successfully."
            error = None
        elif fail_count == total:
            # All failed.
            merged_signal = Signal.FAILED
            summary = f"All {total} branches failed."
            error = ErrorDetail(
                failure_class=FailureClass.LOGIC_ERROR,
                message=f"All {total} branches failed.",
            )
        else:
            # Mixed results → PARTIAL.
            merged_signal = Signal.PARTIAL
            summary = f"Mixed results: {done_count}/{total} passed, {fail_count}/{total} failed."
            error = ErrorDetail(
                failure_class=FailureClass.LOGIC_ERROR,
                message=f"{fail_count} branch(es) failed out of {total}.",
            )

        # Build the result URI from successful branches.
        result_uris = [o.result_uri for o in branch_outputs if o.result_uri]
        result_uri = result_uris[0] if len(result_uris) == 1 else (
            f"uri://aggregated/{self.aggregator_id}" if result_uris else None
        )

        # PARTIAL and DONE require result_uri.
        if merged_signal in (Signal.DONE, Signal.PARTIAL) and result_uri is None:
            result_uri = f"uri://aggregated/{self.aggregator_id}"

        aggregator_output = AggregatorOutput(
            signal=merged_signal,
            node_id=self.aggregator_id,
            orchestrator_summary=summary,
            result_uri=result_uri,
            error_detail=error,
            branch_breakdown=branch_results,
            partial_commit_policy=self.partial_commit_policy,
        )

        return AggregationResult(
            output=aggregator_output,
            branch_outputs=branch_outputs,
        )
