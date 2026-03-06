"""ClawGraph — Signal-based hierarchical agent orchestration."""

from clawgraph.bag.manager import BagManager, BagManifest
from clawgraph.bag.node import ClawNodeMetadata, clawnode
from clawgraph.bag.skills import SkillsContextManager
from clawgraph.core.models import (
    AggregatorOutput,
    ArchiveEntry,
    BagContract,
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
from clawgraph.storage.archive import DocumentArchive
from clawgraph.telemetry.hud import build_hud_snapshot
from clawgraph.telemetry.links import compute_implicit_links

__all__ = [
    "AggregatorOutput",
    "ArchiveEntry",
    "BagContract",
    "BagManager",
    "BagManifest",
    "BagState",
    "BranchResult",
    # Bag
    "ClawBag",
    "ClawNodeMetadata",
    "ClawOutput",
    "DocumentArchive",
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
    # Telemetry
    "build_hud_snapshot",
    "clawnode",
    "compute_implicit_links",
]
