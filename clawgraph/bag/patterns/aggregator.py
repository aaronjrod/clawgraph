"""Aggregator builder -- fan-in/fan-out workflow utility.

Spec ref: 06_patterns.md S3.4
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
    - All DONE -> DONE
    - Any FAILED (with some DONE) -> PARTIAL
    - All FAILED -> FAILED

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
        self._branches.append(
            BranchSpec(
                branch_id=branch_id,
                node_id=node_id,
                fn=fn,
            )
        )

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
            branch_results.append(
                BranchResult(
                    branch_id=spec.branch_id,
                    node_id=spec.node_id,
                    signal=output.signal,
                    summary=output.orchestrator_summary,
                    result_uri=output.result_uri,
                    error_detail=output.error_detail,
                )
            )

        # Merge semantics.
        done_count = sum(1 for o in branch_outputs if o.signal == Signal.DONE)
        fail_count = sum(
            1 for o in branch_outputs if o.signal in (Signal.FAILED, Signal.NEED_INTERVENTION)
        )
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
            # Mixed results -> PARTIAL.
            merged_signal = Signal.PARTIAL
            summary = f"Mixed results: {done_count}/{total} passed, {fail_count}/{total} failed."
            error = ErrorDetail(
                failure_class=FailureClass.LOGIC_ERROR,
                message=f"{fail_count} branch(es) failed out of {total}.",
            )

        # Build the result URI from successful branches.
        result_uris = [o.result_uri for o in branch_outputs if o.result_uri]
        result_uri = (
            result_uris[0]
            if len(result_uris) == 1
            else (f"uri://aggregated/{self.aggregator_id}" if result_uris else None)
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
