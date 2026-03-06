"""Reusable node patterns -- DocumentNode, VerificationNode, AggregatorBuilder.

Re-exports all public symbols so existing imports remain unchanged:
    from clawgraph.bag.patterns import DocumentNode, VerificationNode, ...
"""

from clawgraph.bag.patterns.aggregator import (
    AggregationResult,
    AggregatorBuilder,
    BranchSpec,
)
from clawgraph.bag.patterns.document import DocumentEdit, DocumentNode
from clawgraph.bag.patterns.verification import CheckResult, VerificationNode

__all__ = [
    "AggregationResult",
    "AggregatorBuilder",
    "BranchSpec",
    "CheckResult",
    "DocumentEdit",
    "DocumentNode",
    "VerificationNode",
]
