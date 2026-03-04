"""ClawGraph — Signal-based hierarchical agent orchestration."""

from clawgraph.bag.manager import BagManager, BagManifest
from clawgraph.bag.node import ClawNodeMetadata, clawnode
from clawgraph.bag.skills import SkillsContextManager
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
from clawgraph.core.timeline import TimelineBuffer, TimelineEvent
from clawgraph.orchestrator.graph import BagState, ClawBag

__all__ = [
    "AggregatorOutput",
    "BagManager",
    "BagManifest",
    "BagState",
    "BranchResult",
    # Bag
    "ClawBag",
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
    "SkillsContextManager",
    "TimelineBuffer",
    "TimelineEvent",
    "clawnode",
]
