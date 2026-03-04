"""ClawGraph — Signal-based hierarchical agent orchestration."""

from clawgraph.bag.manager import BagManager, BagManifest
from clawgraph.bag.node import ClawNodeMetadata, clawnode
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
from clawgraph.core.signals import SignalManager

__all__ = [
    "AggregatorOutput",
    "BagManager",
    "BagManifest",
    "BranchResult",
    # Bag
    "ClawNodeMetadata",
    "ClawOutput",
    "ErrorDetail",
    "FailureClass",
    "HumanRequest",
    "InfoRequest",
    # Core models
    "Signal",
    # Signal Manager
    "SignalManager",
    "clawnode",
]
