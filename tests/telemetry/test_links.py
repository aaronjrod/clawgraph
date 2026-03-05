"""TDD tests for implicit link computation (telemetry/links.py)."""

from clawgraph.core.signals import NodeState, NodeStatus
from clawgraph.telemetry.links import compute_implicit_links


class TestComputeImplicitLinks:
    """Tests for the extracted link computation logic."""

    def test_compute_links_from_requires(self):
        """Node A requires doc_result → link to node that produced doc_result."""
        node_states = {
            "doc_producer": NodeState(
                node_id="doc_producer",
                status=NodeStatus.DONE,
                result_uri="uri://doc.pdf",
            ),
            "consumer": NodeState(
                node_id="consumer",
                status=NodeStatus.PENDING,
            ),
        }
        manifest_nodes = {
            "doc_producer": {"requires": []},
            "consumer": {"requires": ["doc_producer_result"]},
        }

        links = compute_implicit_links(node_states, manifest_nodes)
        assert len(links) >= 1
        link = links[0]
        assert link["source"] == "doc_producer"
        assert link["target"] == "consumer"
        assert link["type"] == "data_flow"

    def test_no_spurious_links(self):
        """Node with no requires → no links generated."""
        node_states = {
            "standalone": NodeState(node_id="standalone", status=NodeStatus.DONE),
        }
        manifest_nodes = {
            "standalone": {"requires": []},
        }

        links = compute_implicit_links(node_states, manifest_nodes)
        assert links == []

    def test_links_unresolved_requirement(self):
        """Requirement with no matching producer → no link generated."""
        node_states = {
            "consumer": NodeState(node_id="consumer", status=NodeStatus.PENDING),
        }
        manifest_nodes = {
            "consumer": {"requires": ["missing_artifact"]},
        }

        links = compute_implicit_links(node_states, manifest_nodes)
        assert links == []
