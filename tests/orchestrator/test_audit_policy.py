"""TDD tests for audit_policy enforcement (F-REQ-27, Appendix §1.3)."""

from clawgraph.bag.node import clawnode
from clawgraph.core.models import ClawOutput, Signal
from clawgraph.orchestrator.graph import ClawBag


class TestAuditPolicyEnforcement:
    """Audit policy and audit_hint should produce AUDIT_TRIGGERED events."""

    def test_always_audit_emits_timeline_event(self):
        """Node with audit_policy={"always": True} gets AUDIT_TRIGGERED."""
        bag = ClawBag(name="audit_bag")

        @clawnode(
            id="audited_node",
            description="Always audited.",
            bag="audit_bag",
            audit_policy={"always": True},
        )
        def audited_node(state: dict) -> ClawOutput:  # type: ignore[type-arg]
            return ClawOutput(
                signal=Signal.DONE,
                node_id="audited_node",
                orchestrator_summary="Work done.",
                result_uri="uri://out.json",
            )

        bag.manager.register_node(audited_node)
        result = bag.start_job(objective="Audit test.")

        timeline = result.get("timeline", [])
        audit_events = [e for e in timeline if e.get("signal") == "AUDIT_TRIGGERED"]
        assert len(audit_events) >= 1, "Should have an AUDIT_TRIGGERED event"
        assert audit_events[0]["node_id"] == "audited_node"

    def test_no_policy_no_audit_event(self):
        """Node without audit_policy → no AUDIT_TRIGGERED event."""
        bag = ClawBag(name="no_audit_bag")

        @clawnode(
            id="normal_node",
            description="No audit policy.",
            bag="no_audit_bag",
        )
        def normal_node(state: dict) -> ClawOutput:  # type: ignore[type-arg]
            return ClawOutput(
                signal=Signal.DONE,
                node_id="normal_node",
                orchestrator_summary="Done.",
                result_uri="uri://out.json",
            )

        bag.manager.register_node(normal_node)
        result = bag.start_job(objective="No audit.")

        timeline = result.get("timeline", [])
        audit_events = [e for e in timeline if e.get("signal") == "AUDIT_TRIGGERED"]
        assert len(audit_events) == 0

    def test_audit_hint_true_emits_event(self):
        """Node output with audit_hint=True gets AUDIT_TRIGGERED."""
        bag = ClawBag(name="hint_bag")

        @clawnode(id="hint_node", description="Hints audit.", bag="hint_bag")
        def hint_node(state: dict) -> ClawOutput:  # type: ignore[type-arg]
            return ClawOutput(
                signal=Signal.DONE,
                node_id="hint_node",
                orchestrator_summary="Work with audit hint.",
                result_uri="uri://out.json",
                audit_hint=True,
            )

        bag.manager.register_node(hint_node)
        result = bag.start_job(objective="Hint audit.")

        timeline = result.get("timeline", [])
        audit_events = [e for e in timeline if e.get("signal") == "AUDIT_TRIGGERED"]
        assert len(audit_events) >= 1

    def test_policy_overrides_hint_false(self):
        """audit_policy={"always": True} + audit_hint=False → still triggers."""
        bag = ClawBag(name="override_bag")

        @clawnode(
            id="override_node",
            description="Policy overrides hint.",
            bag="override_bag",
            audit_policy={"always": True},
        )
        def override_node(state: dict) -> ClawOutput:  # type: ignore[type-arg]
            return ClawOutput(
                signal=Signal.DONE,
                node_id="override_node",
                orchestrator_summary="Done.",
                result_uri="uri://out.json",
                audit_hint=False,
            )

        bag.manager.register_node(override_node)
        result = bag.start_job(objective="Override test.")

        timeline = result.get("timeline", [])
        audit_events = [e for e in timeline if e.get("signal") == "AUDIT_TRIGGERED"]
        assert len(audit_events) >= 1, "Policy should override hint=False"
