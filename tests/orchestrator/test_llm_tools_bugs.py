"""TDD tests for bugs discovered during the deep Orchestrator audit.

Bugs covered:
1. `ready_queue` not popping executed nodes (Bug 2.1).
2. Stale `current_output` on `HOLD_FOR_HUMAN` suspend (Bug 2.2).
3. Exponential state duplication in `timeline` and `completed_nodes` (Bug 5.1).
4. `escalate` assuming `_result` suffix for cascading (Bug 2.3).
"""

from clawgraph.core.models import ClawOutput, Signal
from clawgraph.core.signals import SignalManager
from clawgraph.orchestrator.llm_tools import OrchestratorTools


# Helper generic manifest
class MockManifest:
    def __init__(self, nodes=None):
        self.nodes = nodes or {}


class MockMeta:
    def __init__(self, requires=None, audit_policy=None):
        self.requires = requires or []
        self.audit_policy = audit_policy


class MockBagManager:
    def __init__(self, manifest):
        self._manifest = manifest

    @property
    def manifest(self):
        return self._manifest

    def get_node_fn(self, node_id):
        # Default mock returns DONE
        return lambda state: ClawOutput(
            signal=Signal.DONE,
            node_id=node_id,
            orchestrator_summary="Done.",
            result_uri="uri://mock",
        )


class TestLlmToolsBugs:
    def test_bug_2_1_ready_queue_pops_dispatched_node(self):
        """Bug 2.1: dispatch_node should remove the dispatched node from ready_queue."""
        # Setup mock node that just returns DONE
        manifest = MockManifest({"test_node": MockMeta()})
        tools = OrchestratorTools(MockBagManager(manifest), SignalManager())

        state = {
            "ready_queue": ["test_node", "other_node"],
            "stalled_queue": [],
            "document_archive": {},
        }

        updates = tools.dispatch_node(state, {"node_id": "test_node"})

        # test_node should be gone, other_node should remain
        assert "test_node" not in updates.get("ready_queue", state["ready_queue"])
        assert "other_node" in updates.get("ready_queue", state["ready_queue"])

    def test_bug_2_2_suspend_clears_current_output(self):
        """Bug 2.2: suspend should clear/prune current_output so it doesn't carry stale blobs."""
        tools = OrchestratorTools(MockBagManager(MockManifest()), SignalManager())
        state = {
            "current_output": {
                "signal": "DONE",
                "node_id": "previous_node",
                "orchestrator_summary": "I am stale data that wastes context.",
            }
        }

        updates = tools.suspend(state, {"human_request_message": "Approve?"})

        # The new current_output should ONLY contain the HOLD_FOR_HUMAN signal
        # and NOT the previous node's data.
        new_output = updates.get("current_output", {})
        assert new_output.get("signal") == "HOLD_FOR_HUMAN"
        assert new_output.get("node_id") == "orchestrator"
        assert "orchestrator_summary" not in new_output
        # Stale data should be gone
        assert new_output.get("node_id") != "previous_node"

    def test_bug_5_1_dispatch_node_timeline_duplication(self):
        """Bug 5.1: dispatch_node appending to entire timeline history causes duplication in LangGraph."""
        manifest = MockManifest({"stalled_node": MockMeta(requires=["missing_doc"])})
        tools = OrchestratorTools(MockBagManager(manifest), SignalManager())

        state = {
            "timeline": [{"event": "historical"}],
            "document_archive": {},
            "bag_name": "test_bag",
        }

        # Dispatching a node with unmet prereqs triggers a STALLED event update
        updates = tools.dispatch_node(state, {"node_id": "stalled_node"})

        timeline_update = updates.get("timeline")
        assert timeline_update is not None

        # In LangGraph with operator.add, the update should ONLY contain the NEW events.
        # If it contains "historical", LangGraph will result in ["historical", "historical", "new_event"]
        assert len(timeline_update) == 1
        assert timeline_update[0].get("signal") == "STALLED"
        assert "historical" not in [e.get("event") for e in timeline_update]

    def test_bug_5_1_escalate_timeline_duplication(self):
        """Bug 5.1: escalate appending to entire timeline history causes duplication in LangGraph."""
        manifest = MockManifest({"consumer": MockMeta(requires=["producer_failure_trigger"])})
        tools = OrchestratorTools(MockBagManager(manifest), SignalManager())

        state = {
            "timeline": [{"event": "historical"}],
            "completed_nodes": ["historical_node"],
            "stalled_queue": ["consumer"],
            "current_output": {"signal": "FAILED", "node_id": "producer"},
        }

        # For the test to trigger cascade, we need to mock the required artifact matching logic
        # Bug 2.3 notes the hardcoded `_result` suffix. We'll use it here to ensure Bug 5.1 is reached.
        manifest = MockManifest({"consumer": MockMeta(requires=["producer_result"])})
        tools = OrchestratorTools(MockBagManager(manifest), SignalManager())

        # Escalate triggers dead-end cascading
        updates = tools.escalate(state, {"reason": "failed", "failure_class": "LOGIC_ERROR"})

        timeline_update = updates.get("timeline")
        completed_update = updates.get("completed_nodes")

        assert timeline_update is not None
        assert completed_update is not None

        # Bug 5.1: The update must ONLY contain the newly cascaded node, not the historical state
        assert len(timeline_update) == 1
        assert timeline_update[0].get("signal") == "DEAD_END"

        assert len(completed_update) == 1
        assert completed_update[0] == "consumer"

    def test_bug_2_3_escalate_does_not_assume_result_suffix(self):
        """Bug 2.3: escalate should cascade failures based on actual artifact lineage, not hardcoded suffixes."""
        # A consumer requires an artifact named 'custom_artifact_name', not 'producer_result'.
        manifest = MockManifest({"consumer": MockMeta(requires=["custom_artifact_name"])})
        tools = OrchestratorTools(MockBagManager(manifest), SignalManager())

        state = {
            "stalled_queue": ["consumer"],
            "completed_nodes": [],
            "timeline": [],
            "current_output": {"signal": "FAILED", "node_id": "producer"},
        }

        # To fix this bug, we need a way for the Orchestrator to know what artifacts a node
        # produces. Since `ClawNode` outputs `result_uri`, the conventional mapping is ID -> ID_result.
        # But if we want to fix 2.3, the manifest needs an `outputs` mapping, or we accept the convention
        # as a strict rule and document it. For now, the test expects the consumer to NOT cascade
        # if the missing artifact doesn't match the hardcoded `_result` suffix, which proves the
        # limitation exists.

        _updates = tools.escalate(state, {"reason": "failed", "failure_class": "LOGIC_ERROR"})
        pass  # Will implement fix and assertion once we decide how to link them.
