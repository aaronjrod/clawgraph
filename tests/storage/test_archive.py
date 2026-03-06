"""TDD tests for DocumentArchive API (Appendix §2.9).

The DocumentArchive provides a formal put/get/delete/list/tag interface
over the raw document_archive dict, with domain-tag visibility.
"""

from clawgraph.storage.archive import DocumentArchive


class TestDocumentArchive:
    """DocumentArchive CRUD and visibility."""

    def test_put_and_get(self):
        archive = DocumentArchive()
        archive.put("doc1", uri="s3://data/doc.pdf", domain="my_bag", created_by="node_a")
        entry = archive.get("doc1")
        assert entry is not None
        assert entry.uri == "s3://data/doc.pdf"
        assert entry.domain == "my_bag"
        assert entry.created_by == "node_a"

    def test_put_overwrites(self):
        archive = DocumentArchive()
        archive.put("doc1", uri="v1.pdf", domain="bag_a")
        archive.put("doc1", uri="v2.pdf", domain="bag_a")
        entry = archive.get("doc1")
        assert entry is not None
        assert entry.uri == "v2.pdf"

    def test_get_missing_returns_none(self):
        archive = DocumentArchive()
        assert archive.get("nonexistent") is None

    def test_delete(self):
        archive = DocumentArchive()
        archive.put("doc1", uri="s3://doc.pdf", domain="bag_a")
        assert archive.delete("doc1") is True
        assert archive.get("doc1") is None

    def test_delete_missing_returns_false(self):
        archive = DocumentArchive()
        assert archive.delete("nonexistent") is False

    def test_list_all(self):
        archive = DocumentArchive()
        archive.put("a", uri="u1", domain="bag_a")
        archive.put("b", uri="u2", domain="bag_b")
        entries = archive.list_entries()
        assert len(entries) == 2
        assert "a" in entries
        assert "b" in entries

    def test_list_filtered_by_domain(self):
        archive = DocumentArchive()
        archive.put("a", uri="u1", domain="bag_a")
        archive.put("b", uri="u2", domain="bag_b")
        archive.put("c", uri="u3", domain="bag_a")
        entries = archive.list_entries(domain="bag_a")
        assert len(entries) == 2
        assert "a" in entries
        assert "c" in entries

    def test_tag_adds_tags(self):
        archive = DocumentArchive()
        archive.put("doc1", uri="u1", domain="bag_a", tags=["internal"])
        archive.tag("doc1", ["shared", "public"])
        entry = archive.get("doc1")
        assert entry is not None
        assert "internal" in entry.tags
        assert "shared" in entry.tags
        assert "public" in entry.tags

    def test_visible_to_respects_domain(self):
        archive = DocumentArchive()
        archive.put("secret", uri="u1", domain="bag_a", tags=["internal"])
        archive.put("shared", uri="u2", domain="bag_a", tags=["public"])

        # Same domain — always visible
        assert archive.visible_to("secret", "bag_a") is True
        # Other domain, internal — not visible
        assert archive.visible_to("secret", "bag_b") is False
        # Other domain, public — visible
        assert archive.visible_to("shared", "bag_b") is True
        # Missing key — not visible
        assert archive.visible_to("nonexistent", "bag_a") is False

    def test_snapshot_returns_dict(self):
        archive = DocumentArchive()
        archive.put("doc1", uri="u1", domain="bag_a", created_by="node_x")
        snap = archive.snapshot()
        assert isinstance(snap, dict)
        assert "doc1" in snap
        assert snap["doc1"]["uri"] == "u1"
        assert snap["doc1"]["domain"] == "bag_a"
