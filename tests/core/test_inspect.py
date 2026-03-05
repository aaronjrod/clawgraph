"""TDD tests for Timeline Tier 3 inspect (F-REQ-33).

inspect_event() retrieves a timeline event and its corresponding
ArchiveEntry from the document_archive.
"""

from clawgraph.bag.node import clawnode
from clawgraph.core.models import ClawOutput, Signal
from clawgraph.orchestrator.graph import ClawBag


class TestInspectEvent:
    """inspect_event() API on ClawBag."""

    def test_inspect_returns_event_with_archive_entry(self):
        """Event with result_uri should include the matching archive entry."""
        bag = ClawBag(name="inspect_bag")

        @clawnode(id="producer", description="Produces.", bag="inspect_bag")
        def producer(state: dict) -> ClawOutput:  # type: ignore[type-arg]
            return ClawOutput(
                signal=Signal.DONE,
                node_id="producer",
                orchestrator_summary="Produced data.",
                result_uri="uri://data.csv",
            )

        bag.manager.register_node(producer)
        result = bag.start_job(
            objective="Inspect test.",
            thread_id="inspect-thread",
        )

        # Should be able to inspect the latest event for 'producer'
        inspection = bag.inspect_event(
            thread_id="inspect-thread",
            node_id="producer",
        )

        assert inspection is not None
        assert inspection["node_id"] == "producer"
        assert "archive_entry" in inspection
        entry = inspection["archive_entry"]
        assert entry["uri"] == "uri://data.csv"

    def test_inspect_missing_node_returns_none(self):
        """Non-existent node → None."""
        bag = ClawBag(name="empty_inspect_bag")

        @clawnode(id="filler", description="Filler.", bag="empty_inspect_bag")
        def filler(state: dict) -> ClawOutput:  # type: ignore[type-arg]
            return ClawOutput(
                signal=Signal.DONE,
                node_id="filler",
                orchestrator_summary="Done.",
                result_uri="uri://out.json",
            )

        bag.manager.register_node(filler)
        bag.start_job(objective="Empty inspect.", thread_id="empty-thread")

        inspection = bag.inspect_event(
            thread_id="empty-thread",
            node_id="nonexistent",
        )
        assert inspection is None
