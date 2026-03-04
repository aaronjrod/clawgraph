"""Tests for clawgraph.bag — BagManager, @clawnode decorator, and inventory."""

import pytest

from clawgraph.bag.manager import BagManager
from clawgraph.bag.node import ClawNodeMetadata, clawnode
from clawgraph.core.exceptions import ManifestLockedError
from clawgraph.core.models import ClawOutput, Signal

# ── Fixtures ───────────────────────────────────────────────────────────────────


@clawnode(
    id="summarize_doc",
    description="Summarizes a document.",
    bag="test_bag",
    skills=["summarization.md"],
    tags=["nlp"],
)
def sample_node(state: dict) -> ClawOutput:
    return ClawOutput(
        signal=Signal.DONE,
        node_id="summarize_doc",
        orchestrator_summary="Summarized.",
        result_uri="uri://summary.json",
    )


@clawnode(
    id="verify_output",
    description="Verifies node outputs.",
    bag="test_bag",
    tags=["verification"],
)
def verify_node(state: dict) -> ClawOutput:
    return ClawOutput(
        signal=Signal.DONE,
        node_id="verify_output",
        orchestrator_summary="Verified.",
        result_uri="uri://verify.json",
    )


def bare_function(state: dict) -> dict:
    """A function without @clawnode decorator."""
    return {"result": "raw"}


# ── @clawnode Decorator ────────────────────────────────────────────────────────


class TestClawnodeDecorator:
    def test_metadata_attached(self):
        meta = sample_node._clawnode_metadata
        assert isinstance(meta, ClawNodeMetadata)
        assert meta.id == "summarize_doc"
        assert meta.bag == "test_bag"
        assert meta.skills == ["summarization.md"]
        assert meta.tags == ["nlp"]

    def test_function_still_callable(self):
        result = sample_node({})
        assert isinstance(result, ClawOutput)
        assert result.signal == Signal.DONE

    def test_non_clawoutput_return_raises(self):
        @clawnode(id="bad_node", description="Returns wrong type.", bag="test")
        def bad_node(state: dict) -> dict:
            return {"oops": True}

        with pytest.raises(TypeError, match="must return a ClawOutput"):
            bad_node({})

    def test_preserves_function_name(self):
        assert sample_node.__name__ == "sample_node"


# ── BagManager CRUD ────────────────────────────────────────────────────────────


class TestBagManagerCRUD:
    def test_register_decorated_node(self):
        bag = BagManager(name="test")
        meta = bag.register_node(sample_node)
        assert meta.id == "summarize_doc"
        assert "summarize_doc" in bag
        assert bag.version == 1

    def test_register_with_explicit_metadata(self):
        bag = BagManager(name="test")
        meta = ClawNodeMetadata(id="custom", description="Custom node.", bag="test")
        bag.register_node(bare_function, metadata=meta)
        assert "custom" in bag
        assert bag.version == 1

    def test_register_without_metadata_raises(self):
        bag = BagManager(name="test")
        with pytest.raises(ValueError, match="No metadata found"):
            bag.register_node(bare_function)

    def test_register_increments_version(self):
        bag = BagManager(name="test")
        bag.register_node(sample_node)
        bag.register_node(verify_node)
        assert bag.version == 2

    def test_update_node(self):
        bag = BagManager(name="test")
        bag.register_node(sample_node)
        updated = bag.update_node("summarize_doc", description="Updated description.")
        assert updated.description == "Updated description."
        assert bag.version == 2

    def test_update_nonexistent_raises(self):
        bag = BagManager(name="test")
        with pytest.raises(KeyError, match="not found"):
            bag.update_node("ghost_node", description="nope")

    def test_delete_node(self):
        bag = BagManager(name="test")
        bag.register_node(sample_node)
        assert "summarize_doc" in bag

        removed = bag.delete_node("summarize_doc")
        assert removed.id == "summarize_doc"
        assert "summarize_doc" not in bag
        assert bag.version == 2

    def test_delete_nonexistent_raises(self):
        bag = BagManager(name="test")
        with pytest.raises(KeyError, match="not found"):
            bag.delete_node("ghost_node")

    def test_get_node_fn(self):
        bag = BagManager(name="test")
        bag.register_node(sample_node)
        fn = bag.get_node_fn("summarize_doc")
        assert callable(fn)

    def test_len_and_contains(self):
        bag = BagManager(name="test")
        assert len(bag) == 0
        bag.register_node(sample_node)
        assert len(bag) == 1
        assert "summarize_doc" in bag

    def test_repr(self):
        bag = BagManager(name="test")
        assert "test" in repr(bag)
        assert "version=0" in repr(bag)


# ── Manifest Locking ──────────────────────────────────────────────────────────


class TestManifestLocking:
    def test_locked_rejects_register(self):
        bag = BagManager(name="test")
        bag.lock()
        with pytest.raises(ManifestLockedError):
            bag.register_node(sample_node)

    def test_locked_rejects_update(self):
        bag = BagManager(name="test")
        bag.register_node(sample_node)
        bag.lock()
        with pytest.raises(ManifestLockedError):
            bag.update_node("summarize_doc", description="nope")

    def test_locked_rejects_delete(self):
        bag = BagManager(name="test")
        bag.register_node(sample_node)
        bag.lock()
        with pytest.raises(ManifestLockedError):
            bag.delete_node("summarize_doc")

    def test_unlock_allows_crud(self):
        bag = BagManager(name="test")
        bag.lock()
        bag.unlock()
        bag.register_node(sample_node)  # Should not raise.
        assert "summarize_doc" in bag


# ── Inventory ──────────────────────────────────────────────────────────────────


class TestInventory:
    def test_empty_inventory(self):
        bag = BagManager(name="test")
        inv = bag.get_inventory()
        assert inv["bag"] == "test"
        assert inv["version"] == 0
        assert inv["node_count"] == 0
        assert inv["nodes"] == {}

    def test_inventory_returns_tier1_only(self):
        bag = BagManager(name="test")
        bag.register_node(sample_node)
        inv = bag.get_inventory()
        assert inv["node_count"] == 1
        node_info = inv["nodes"]["summarize_doc"]
        assert "description" in node_info
        assert "tags" in node_info
        # Tier 1 only — no code, no raw artifacts.
        assert "code" not in node_info
        assert "function" not in node_info

    def test_inventory_marks_discovery(self):
        bag = BagManager(name="test")
        assert bag._inventory_queried is False
        bag.get_inventory()
        assert bag._inventory_queried is True


# ── Audit Node ─────────────────────────────────────────────────────────────────


class TestAuditNode:
    def test_audit_returns_source_and_metadata(self):
        bag = BagManager(name="test")
        bag.register_node(sample_node)
        audit = bag.audit_node("summarize_doc")
        assert audit["node_id"] == "summarize_doc"
        assert audit["metadata"]["id"] == "summarize_doc"
        assert audit["source"] is not None
        assert "def sample_node" in audit["source"]

    def test_audit_unknown_node_raises(self):
        bag = BagManager(name="test")
        with pytest.raises(KeyError, match="not found"):
            bag.audit_node("ghost")

    def test_audit_returns_audit_policy(self):
        bag = BagManager(name="test")
        meta = ClawNodeMetadata(
            id="audited",
            description="Has policy.",
            bag="test",
            audit_policy={"always": True},
        )
        bag.register_node(bare_function, metadata=meta)
        audit = bag.audit_node("audited")
        assert audit["audit_policy"] == {"always": True}

    def test_audit_no_policy_returns_none(self):
        bag = BagManager(name="test")
        bag.register_node(sample_node)
        audit = bag.audit_node("summarize_doc")
        assert audit["audit_policy"] is None


# ── Rollback ───────────────────────────────────────────────────────────────────


class TestRollback:
    def test_rollback_to_earlier_version(self):
        bag = BagManager(name="test")
        bag.register_node(sample_node)  # v1: has summarize_doc
        bag.register_node(verify_node)  # v2: has both
        assert len(bag) == 2
        assert bag.version == 2

        bag.rollback_bag(version=1)
        assert bag.version == 1
        assert "summarize_doc" in bag
        assert "verify_output" not in bag

    def test_rollback_preserves_history(self):
        bag = BagManager(name="test")
        bag.register_node(sample_node)  # v1
        bag.register_node(verify_node)  # v2
        assert len(bag._manifest_history) == 2

        bag.rollback_bag(version=1)
        # History should still contain snapshots.
        assert len(bag._manifest_history) >= 2

    def test_rollback_unknown_version_raises(self):
        bag = BagManager(name="test")
        bag.register_node(sample_node)
        with pytest.raises(ValueError, match="not found in history"):
            bag.rollback_bag(version=99)

    def test_rollback_locked_raises(self):
        bag = BagManager(name="test")
        bag.register_node(sample_node)
        bag.lock()
        with pytest.raises(ManifestLockedError):
            bag.rollback_bag(version=0)

