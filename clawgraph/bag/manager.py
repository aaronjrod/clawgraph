"""BagManager -- node registration, manifest versioning, and lifecycle.

The BagManager owns the versioned manifest and provides the CRUD API
that the Super-Orchestrator uses to build and modify bags.

Spec ref: 03_FRS.md S2.1, 05_ARCHITECTURE.md S3
"""

from __future__ import annotations

import inspect
import logging
from collections.abc import Callable
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from clawgraph.bag.node import ClawNodeMetadata
from clawgraph.core.exceptions import ManifestLockedError

logger = logging.getLogger(__name__)


class BagManifest(BaseModel):
    """Versioned manifest of all nodes in a bag. (F-REQ-3, F-REQ-4)

    The manifest stores Tier 1 metadata only — descriptions, tags, and
    capabilities. Node code (Tier 2) and raw artifacts (Tier 3) are stored
    separately and accessed via audit_node().
    """

    name: str
    version: int = 0
    nodes: dict[str, ClawNodeMetadata] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)


class BagManager:
    """Manages node registration, manifest versioning, and bag lifecycle.

    Usage:
        bag = BagManager(name="research_ops")
        bag.register_node(summarize_doc)  # decorated with @clawnode
        bag.register_node(verify_output)
        inventory = bag.get_inventory()
    """

    def __init__(self, name: str) -> None:
        self._manifest = BagManifest(name=name)
        self._node_fns: dict[str, Callable[..., Any]] = {}  # node_id -> actual function (Tier 2)
        self._locked: bool = False
        self._inventory_queried: bool = False
        self._manifest_history: list[BagManifest] = []  # Version snapshots for rollback.

    @property
    def manifest(self) -> BagManifest:
        """The current manifest (read-only access)."""
        return self._manifest

    @property
    def name(self) -> str:
        return self._manifest.name

    @property
    def version(self) -> int:
        return self._manifest.version

    @property
    def locked(self) -> bool:
        return self._locked

    def lock(self) -> None:
        """Lock the manifest to prevent mutation during active jobs."""
        self._locked = True
        logger.info("Bag '%s' manifest locked at v%d.", self.name, self.version)

    def unlock(self) -> None:
        """Unlock the manifest after job completion."""
        self._locked = False
        logger.info("Bag '%s' manifest unlocked.", self.name)

    # ── CRUD Operations ────────────────────────────────────────────

    def register_node(
        self,
        node_fn: Callable[..., Any],
        metadata: ClawNodeMetadata | None = None,
    ) -> ClawNodeMetadata:
        """Register a node into the bag. (F-REQ-1)

        If node_fn is decorated with @clawnode, metadata is extracted
        automatically. Otherwise, metadata must be provided explicitly.

        Args:
            node_fn: The node function (optionally decorated with @clawnode).
            metadata: Explicit metadata. Overrides decorator metadata if both exist.

        Returns:
            The registered ClawNodeMetadata.

        Raises:
            ManifestLockedError: If the manifest is locked.
            ValueError: If no metadata is available.
        """
        self._check_locked()
        self._warn_discovery_first()

        # Extract metadata from decorator if not explicitly provided.
        if metadata is None:
            metadata = getattr(node_fn, "_clawnode_metadata", None)
        if metadata is None:
            raise ValueError(
                f"No metadata found for node function '{node_fn.__name__}'. "
                f"Either decorate with @clawnode or pass metadata explicitly."
            )

        if metadata.id in self._manifest.nodes:
            logger.warning(
                "Node '%s' already registered in bag '%s'. Overwriting.",
                metadata.id,
                self.name,
            )

        self._manifest.nodes[metadata.id] = metadata
        self._node_fns[metadata.id] = node_fn
        self._bump_version()

        logger.info(
            "Registered node '%s' in bag '%s' (v%d).",
            metadata.id,
            self.name,
            self.version,
        )
        return metadata

    def update_node(
        self,
        node_id: str,
        *,
        node_fn: Callable[..., Any] | None = None,
        metadata: ClawNodeMetadata | None = None,
        **field_updates: Any,
    ) -> ClawNodeMetadata:
        """Update an existing node's code and/or metadata. (F-REQ-1)

        Args:
            node_id: ID of the node to update.
            node_fn: New function implementation (Tier 2 update).
            metadata: Full replacement metadata.
            **field_updates: Partial metadata field updates (e.g., description="new").

        Returns:
            The updated ClawNodeMetadata.

        Raises:
            ManifestLockedError: If the manifest is locked.
            KeyError: If node_id doesn't exist.
        """
        self._check_locked()

        if node_id not in self._manifest.nodes:
            raise KeyError(f"Node '{node_id}' not found in bag '{self.name}'.")

        if node_fn is not None:
            self._node_fns[node_id] = node_fn

        if metadata is not None:
            # Full replacement.
            self._manifest.nodes[node_id] = metadata
        elif field_updates:
            # Partial update.
            current = self._manifest.nodes[node_id]
            updated = current.model_copy(update=field_updates)
            self._manifest.nodes[node_id] = updated

        self._bump_version()

        logger.info(
            "Updated node '%s' in bag '%s' (v%d).",
            node_id,
            self.name,
            self.version,
        )
        return self._manifest.nodes[node_id]

    def delete_node(self, node_id: str) -> ClawNodeMetadata:
        """Remove a node from the bag. (F-REQ-1)

        Args:
            node_id: ID of the node to remove.

        Returns:
            The removed ClawNodeMetadata.

        Raises:
            ManifestLockedError: If the manifest is locked.
            KeyError: If node_id doesn't exist.
        """
        self._check_locked()

        if node_id not in self._manifest.nodes:
            raise KeyError(f"Node '{node_id}' not found in bag '{self.name}'.")

        removed = self._manifest.nodes.pop(node_id)
        self._node_fns.pop(node_id, None)
        self._bump_version()

        logger.info(
            "Deleted node '%s' from bag '%s' (v%d).",
            node_id,
            self.name,
            self.version,
        )
        return removed

    def get_node_fn(self, node_id: str) -> Callable[..., Any]:
        """Retrieve a node's function by ID (Tier 2 access)."""
        if node_id not in self._node_fns:
            raise KeyError(f"Node function '{node_id}' not found in bag '{self.name}'.")
        return self._node_fns[node_id]

    # ── Inventory ──────────────────────────────────────────────────

    def get_inventory(self) -> dict[str, Any]:
        """Return a Tier 1 manifest summary for SO consumption. (F-REQ-21)

        Marks the bag as inventory-queried (Discovery-First discipline).
        """
        self._inventory_queried = True
        return {
            "bag": self.name,
            "version": self.version,
            "node_count": len(self._manifest.nodes),
            "nodes": {
                node_id: {
                    "description": meta.description,
                    "tags": meta.tags,
                    "requires": meta.requires,
                    "provider": meta.provider,
                    "model": meta.model,
                }
                for node_id, meta in self._manifest.nodes.items()
            },
        }

    # ── Audit ──────────────────────────────────────────────────────

    def audit_node(self, node_id: str) -> dict[str, Any]:
        """Return Tier 2 source + Tier 1 metadata for a node. (F-REQ-19, F-REQ-27)

        The Super-Orchestrator uses this to inspect node internals when
        summaries are insufficient or debugging is required.

        Args:
            node_id: ID of the node to audit.

        Returns:
            A dict containing 'metadata', 'source', and 'audit_policy'.

        Raises:
            KeyError: If node_id doesn't exist.
        """
        if node_id not in self._manifest.nodes:
            raise KeyError(f"Node '{node_id}' not found in bag '{self.name}'.")

        meta = self._manifest.nodes[node_id]
        node_fn = self._node_fns.get(node_id)

        # Extract source code (Tier 2).
        source: str | None = None
        if node_fn is not None:
            try:
                # Unwrap @clawnode decorator to get the original function.
                original = getattr(node_fn, "__wrapped__", node_fn)
                source = inspect.getsource(original)
            except (OSError, TypeError):
                source = "<source unavailable>"

        return {
            "node_id": node_id,
            "metadata": meta.model_dump(),
            "source": source,
            "audit_policy": meta.audit_policy,
        }

    # ── Rollback ──────────────────────────────────────────────────

    def rollback_bag(self, version: int) -> BagManifest:
        """Revert the manifest to a prior version. (Architecture S11)

        Restores the Tier 1 manifest from version history. Does NOT
        delete artifacts from the Document Archive (orphaned pointers
        are expected -- see 06_patterns.md S4.4).

        Args:
            version: The manifest version to revert to.

        Returns:
            The restored BagManifest.

        Raises:
            ManifestLockedError: If the manifest is locked.
            ValueError: If the version is not found in history.
        """
        self._check_locked()

        # Find the snapshot with the requested version.
        target: BagManifest | None = None
        for snapshot in self._manifest_history:
            if snapshot.version == version:
                target = snapshot
                break

        if target is None:
            available = [s.version for s in self._manifest_history]
            raise ValueError(
                f"Version {version} not found in history for bag '{self.name}'. "
                f"Available versions: {available}"
            )

        # Restore manifest (deep copy to avoid shared references).
        self._manifest = target.model_copy(deep=True)

        # Remove node functions for nodes no longer in the manifest.
        current_ids = set(self._manifest.nodes.keys())
        stale_ids = set(self._node_fns.keys()) - current_ids
        for stale_id in stale_ids:
            del self._node_fns[stale_id]

        logger.info(
            "Rolled back bag '%s' to v%d (%d nodes).",
            self.name,
            version,
            len(self._manifest.nodes),
        )
        return self._manifest

    # ── Internal ───────────────────────────────────────────────────

    def _check_locked(self) -> None:
        """Raise if the manifest is locked."""
        if self._locked:
            raise ManifestLockedError(self.name)

    def _warn_discovery_first(self) -> None:
        """Advisory warning if CRUD is called before inventory query. (B-REQ-9)"""
        if not self._inventory_queried:
            logger.warning(
                "CRUD operation on bag '%s' before get_inventory() was called. "
                "Discovery-First discipline recommends querying inventory first.",
                self.name,
            )

    def _bump_version(self) -> None:
        """Increment manifest version and update timestamp. (F-REQ-4)"""
        self._manifest.version += 1
        self._manifest.updated_at = datetime.now()
        # Snapshot the manifest at this new version for rollback.
        self._manifest_history.append(self._manifest.model_copy(deep=True))

    def __len__(self) -> int:
        return len(self._manifest.nodes)

    def __contains__(self, node_id: str) -> bool:
        return node_id in self._manifest.nodes

    def __repr__(self) -> str:
        return f"BagManager(name='{self.name}', version={self.version}, nodes={len(self)})"
