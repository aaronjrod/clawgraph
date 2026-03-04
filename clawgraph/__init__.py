"""ClawGraph — Signal-based hierarchical agent orchestration."""

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
from clawgraph.bag.node import ClawNodeMetadata, clawnode
from clawgraph.bag.manager import BagManager, BagManifest

__all__ = [
    # Core models
    "Signal",
    "FailureClass",
    "ErrorDetail",
    "InfoRequest",
    "HumanRequest",
    "BranchResult",
    "ClawOutput",
    "AggregatorOutput",
    # Signal Manager
    "SignalManager",
    # Bag
    "ClawNodeMetadata",
    "clawnode",
    "BagManager",
    "BagManifest",
]
