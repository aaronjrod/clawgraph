"""Implicit link computation — data-flow dependency detection. (Appendix §1.11)

Scans manifest ``requires`` fields against node result_uris to produce
data-flow links for HUD visualization.
"""

from __future__ import annotations

from typing import Any

from clawgraph.core.signals import NodeState


def compute_implicit_links(
    node_states: dict[str, NodeState],
    manifest_nodes: dict[str, Any],
) -> list[dict[str, str]]:
    """Compute data-flow links from requires → producer result_uris.

    Args:
        node_states: Live node state buffer from SignalManager.
        manifest_nodes: Manifest node metadata dict.

    Returns:
        List of link dicts with 'source', 'target', 'type' keys.
    """
    if not manifest_nodes:
        return []

    # Build a map of {result_key: producer_node_id}.
    producer_map: dict[str, str] = {}
    for nid in node_states:
        producer_map[f"{nid}_result"] = nid

    links: list[dict[str, str]] = []
    for node_id, meta in manifest_nodes.items():
        requires = meta.get("requires", []) if isinstance(meta, dict) else []
        for req in requires:
            producer_id = producer_map.get(req)
            if producer_id and producer_id != node_id:
                links.append(
                    {
                        "source": producer_id,
                        "target": node_id,
                        "type": "data_flow",
                    }
                )

    return links
