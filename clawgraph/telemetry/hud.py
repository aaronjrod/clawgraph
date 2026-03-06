"""HUD snapshot builder — extracted from SignalManager. (F-REQ-18, F-REQ-29)

Combines SignalManager live state with manifest topology to produce the
full snapshot for Mission Control rendering.
"""

from __future__ import annotations

from typing import Any

from clawgraph.core.signals import NodeStatus, SignalManager
from clawgraph.telemetry.links import compute_implicit_links


def build_hud_snapshot(
    signal_manager: SignalManager,
    thread_id: str = "",
    manifest_nodes: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build the merged HUD snapshot (Part 7.1 JSON shape).

    Args:
        signal_manager: The live SignalManager.
        thread_id: The current job thread ID.
        manifest_nodes: Manifest node metadata dict (from get_inventory).

    Returns:
        Dict with 'thread_id', 'nodes', and 'links' arrays.
    """
    nodes: list[dict[str, Any]] = []
    links: list[dict[str, str]] = []

    # Collect all known node IDs.
    all_ids = set(signal_manager._node_states.keys())
    if manifest_nodes:
        all_ids |= set(manifest_nodes.keys())

    # Compute data-flow links.
    data_flow_links = compute_implicit_links(
        signal_manager._node_states, manifest_nodes or {},
    )

    for node_id in sorted(all_ids):
        state = signal_manager._node_states.get(node_id)

        node_entry: dict[str, Any] = {
            "id": node_id,
            "name": node_id,
            "status": state.status.value if state else NodeStatus.PENDING.value,
            "last_signal": (
                state.last_signal.value if state and state.last_signal else None
            ),
            "summary": state.last_summary if state else None,
            "result_uri": state.result_uri if state else None,
        }
        nodes.append(node_entry)

        # Topology link: orchestrator -> node.
        links.append({
            "source": "orchestrator",
            "target": node_id,
            "type": "topology",
        })

    # Append data-flow links.
    links.extend(data_flow_links)

    return {
        "thread_id": thread_id,
        "nodes": nodes,
        "links": links,
    }
