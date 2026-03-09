
"""End-to-end integration test — exercises the full ClawBag lifecycle.

Covers:
1. Producer → consumer prereq dependency (stall + resolve)
2. HITL suspension + resume
3. NEED_INFO retry within budget
4. Aggregator with partial commit (eager)
5. Archive visibility enforcement (domain-tagged entry)
"""

from clawgraph.bag.node import clawnode
from clawgraph.core.models import (
    AggregatorOutput,
    ArchiveEntry,
    BranchResult,
    ClawOutput,
    ErrorDetail,
    FailureClass,
    HumanRequest,
    InfoRequest,
    Signal,
)
from clawgraph.orchestrator.graph import ClawBag, _entry_visible


class TestE2ELifecycle:
    """Full lifecycle: producer → prereq stall → resolve → consumer → DONE."""

    def test_full_producer_consumer_lifecycle(self, mock_gemini):
        bag = ClawBag(name="integration_bag")

        @clawnode(id="data_producer", description="Produces data.", bag="integration_bag")
        def data_producer(state: dict) -> ClawOutput:  # type: ignore[type-arg]
            return ClawOutput(
                signal=Signal.DONE,
                node_id="data_producer",
                orchestrator_summary="Produced dataset.",
                result_uri="s3://data/output.csv",
            )

        @clawnode(
            id="data_consumer",
            description="Consumes data.",
            bag="integration_bag",
            requires=["data_producer_result"],
        )
        def data_consumer(state: dict) -> ClawOutput:  # type: ignore[type-arg]
            return ClawOutput(
                signal=Signal.DONE,
                node_id="data_consumer",
                orchestrator_summary="Consumed and transformed data.",
                result_uri="s3://data/transformed.csv",
            )

        # Register consumer first to challenge ordering
        bag.manager.register_node(data_consumer)
        bag.manager.register_node(data_producer)

        # Prime the mock for the multi-turn lifecycle:
        # 1. Dispatch producer
        # 2. Dispatch consumer (which will stall, then resolve)
        # 3. Complete
        mock_gemini.add_expected_call("dispatch_node", {"node_id": "data_producer"}, text="Thinking: I need to produce the data first.")
        mock_gemini.add_expected_call("dispatch_node", {"node_id": "data_consumer"}, text="Thinking: Now that data is available, I can consume it.")
        mock_gemini.add_expected_call("complete", {"final_summary": "E2E success"}, text="Thinking: All nodes completed successfully.")

        result = bag.start_job(objective="Produce and consume data.", inputs={})
        assert result is not None

        # Both nodes should complete
        archive = result.get("document_archive", {})
        assert "data_producer_result" in archive
        assert "data_consumer_result" in archive

        # Archive entries should be ArchiveEntry dicts
        producer_entry = archive["data_producer_result"]
        assert isinstance(producer_entry, dict)
        assert producer_entry["uri"] == "s3://data/output.csv"
        assert producer_entry["domain"] == "integration_bag"
        assert producer_entry["created_by"] == "data_producer"

        # Timeline should have STALLED + RESOLVING events
        timeline = result.get("timeline", [])
        stall_events = [e for e in timeline if e.get("signal") == "STALLED"]
        resolve_events = [e for e in timeline if e.get("signal") == "RESOLVING"]
        assert len(stall_events) >= 1, "Consumer should have been stalled"
        assert len(resolve_events) >= 1, "Should have resolved after producer"

        # Queues should be drained
        assert result.get("stalled_queue", []) == []
        assert result.get("ready_queue", []) == []
        assert len(result.get("completed_nodes", [])) == 2


class TestE2EWithHITL:
    """HITL suspension: node signals HOLD_FOR_HUMAN, handler receives context."""

    def test_hitl_suspension_and_resume(self, mock_gemini):
        bag = ClawBag(name="hitl_bag")

        @clawnode(id="approval_gate", description="Requests approval.", bag="hitl_bag")
        def approval_gate(state: dict) -> ClawOutput:  # type: ignore[type-arg]
            return ClawOutput(
                signal=Signal.HOLD_FOR_HUMAN,
                node_id="approval_gate",
                orchestrator_summary="Requesting deployment approval.",
                human_request=HumanRequest(
                    message="Approve deployment of v2.1?",
                    action_type="deploy_approval",
                ),
            )

        bag.manager.register_node(approval_gate)

        delivered: list[dict] = []  # type: ignore[type-arg]

        def handler(tid: str, req: dict) -> None:  # type: ignore[type-arg]
            delivered.append(req)

        bag.register_hitl_handler(handler)

        # Prime mock to suspend
        mock_gemini.add_expected_call("suspend", {"human_request_message": "Approve deployment?"}, text="Thinking: This is a sensitive operation, I need human approval.")

        result = bag.start_job(objective="Deploy with approval.")

        assert result.get("suspended") is True
        assert len(delivered) == 1
        assert "Approve deployment" in delivered[0].get("message", "")


class TestE2ENeedInfoRetry:
    """NEED_INFO within budget: node retries instead of escalating."""

    def test_need_info_does_not_immediately_escalate(self, mock_gemini):
        bag = ClawBag(name="info_bag")

        call_count = {"n": 0}

        @clawnode(id="clarify_node", description="Needs info.", bag="info_bag")
        def clarify_node(state: dict) -> ClawOutput:  # type: ignore[type-arg]
            call_count["n"] += 1
            if call_count["n"] == 1:
                return ClawOutput(
                    signal=Signal.NEED_INFO,
                    node_id="clarify_node",
                    orchestrator_summary="Need format clarification.",
                    info_request=InfoRequest(
                        question="What format?",
                        context="Output format is ambiguous.",
                    ),
                )
            return ClawOutput(
                signal=Signal.DONE,
                node_id="clarify_node",
                orchestrator_summary="Formatted output.",
                result_uri="uri://output.json",
            )

        bag.manager.register_node(clarify_node)

        # Prime mock to dispatch twice
        mock_gemini.add_expected_call("dispatch_node", {"node_id": "clarify_node"}, text="Thinking: First attempt, might need info.")
        mock_gemini.add_expected_call("dispatch_node", {"node_id": "clarify_node"}, text="Thinking: Retrying after receiving info.")
        mock_gemini.add_expected_call("complete", {"final_summary": "Done after retry"}, text="Thinking: Work is now complete.")

        result = bag.start_job(objective="Clarify and produce.", max_iterations=5)

        # The node should have been called at least twice (once NEED_INFO, once DONE)
        assert call_count["n"] >= 2
        output = result.get("current_output", {})
        assert output.get("signal") == Signal.DONE


class TestE2EAggregatorPartialCommit:
    """Aggregator with eager partial commit: successful branches committed."""

    def test_eager_aggregator_commits_partial(self, mock_gemini):
        bag = ClawBag(name="agg_bag")

        @clawnode(id="quality_gate", description="Aggregates.", bag="agg_bag")
        def quality_gate(state: dict) -> ClawOutput:  # type: ignore[type-arg]
            return AggregatorOutput(
                signal=Signal.PARTIAL,
                node_id="quality_gate",
                orchestrator_summary="Partial: lint passed, tests failed.",
                result_uri="uri://quality_report.json",
                partial_commit_policy="eager",
                error_detail=ErrorDetail(
                    failure_class=FailureClass.LOGIC_ERROR,
                    message="Tests failed.",
                ),
                branch_breakdown=[
                    BranchResult(
                        branch_id="lint",
                        node_id="lint_check",
                        signal=Signal.DONE,
                        summary="Lint passed.",
                        result_uri="uri://lint.json",
                    ),
                    BranchResult(
                        branch_id="tests",
                        node_id="test_runner",
                        signal=Signal.FAILED,
                        summary="3 tests failed.",
                        error_detail=ErrorDetail(
                            failure_class=FailureClass.LOGIC_ERROR,
                            message="3 test failures.",
                        ),
                    ),
                ],
            )

        bag.manager.register_node(quality_gate)

        # Aggregator emits PARTIAL. In LLM mode, PARTIAL isn't a special routing signal anymore,
        # it just means the node finished its turn with partial results.
        # The Orchestrator decides whether to complete or dispatch more.
        mock_gemini.add_expected_call("dispatch_node", {"node_id": "quality_gate"}, text="Thinking: Running the quality gate aggregator.")
        mock_gemini.add_expected_call("complete", {"final_summary": "Aggregated"}, text="Thinking: Aggregation complete, even with partial results.")

        result = bag.start_job(objective="Run quality gate.")

        archive = result.get("document_archive", {})
        # Eager: lint (DONE) should be committed
        assert "lint_result" in archive
        lint_entry = archive["lint_result"]
        assert lint_entry["uri"] == "uri://lint.json"
        assert lint_entry["created_by"] == "lint_check"
        # Atomic-like: tests (FAILED) should NOT produce an entry
        assert "tests_result" not in archive


class TestE2EDomainVisibility:
    """Domain-tag visibility: internal docs from other bags are not visible."""

    def test_cross_bag_internal_blocked(self, mock_gemini):
        """A node requiring a doc tagged 'internal' from another bag should stall."""
        bag = ClawBag(name="my_bag")

        @clawnode(
            id="reader",
            description="Reads a doc.",
            bag="my_bag",
            requires=["classified_doc"],
        )
        def reader(state: dict) -> ClawOutput:  # type: ignore[type-arg]
            return ClawOutput(
                signal=Signal.DONE,
                node_id="reader",
                orchestrator_summary="Read doc.",
                result_uri="uri://summary.txt",
            )

        bag.manager.register_node(reader)

        # Inject a doc from another domain, tagged internal (not visible)
        foreign_entry = ArchiveEntry(
            uri="s3://other_bag/secret.pdf",
            domain="other_bag",
            tags=["internal"],
            created_by="other_node",
        ).model_dump()

        # If it stalls, the tool dispatch_node returns updates with signal=None.
        # The LLM sees this and should eventually complete or escalate.
        mock_gemini.add_expected_call("dispatch_node", {"node_id": "reader"}, text="Thinking: Attempting to read the document.")
        mock_gemini.add_expected_call("complete", {"final_summary": "Stalled out"}, text="Thinking: Document is not visible from this domain. Finishing for now.")

        result = bag.start_job(
            objective="Read classified doc.",
            inputs={"classified_doc": foreign_entry},
        )

        # The reader should NOT have executed — doc is not visible
        assert "reader" not in result.get("completed_nodes", [])
        output = result.get("current_output", {})
        assert output.get("node_id") == "orchestrator"
        assert output.get("signal") == Signal.DONE

    def test_cross_bag_public_allowed(self, mock_gemini):
        """A node requiring a doc tagged 'public' from another bag should proceed."""
        bag = ClawBag(name="my_bag")

        @clawnode(
            id="reader",
            description="Reads a doc.",
            bag="my_bag",
            requires=["shared_doc"],
        )
        def reader(state: dict) -> ClawOutput:  # type: ignore[type-arg]
            return ClawOutput(
                signal=Signal.DONE,
                node_id="reader",
                orchestrator_summary="Read shared doc.",
                result_uri="uri://summary.txt",
            )

        bag.manager.register_node(reader)

        # Inject a doc from another domain, tagged public (visible)
        public_entry = ArchiveEntry(
            uri="s3://other_bag/shared.pdf",
            domain="other_bag",
            tags=["public"],
            created_by="other_node",
        ).model_dump()

        # Should proceed
        mock_gemini.add_expected_call("dispatch_node", {"node_id": "reader"}, text="Thinking: Reading the public shared document.")
        mock_gemini.add_expected_call("complete", {"final_summary": "Allowed"}, text="Thinking: Successfully read the public document.")

        result = bag.start_job(
            objective="Read shared doc.",
            inputs={"shared_doc": public_entry},
        )

        output = result.get("current_output", {})
        assert output.get("signal") == Signal.DONE
        archive = result.get("document_archive", {})
        assert "reader_result" in archive


class TestEntryVisible:
    """Unit tests for the _entry_visible helper function."""

    def test_none_not_visible(self):
        assert not _entry_visible(None, "my_bag")

    def test_legacy_string_always_visible(self):
        assert _entry_visible("s3://legacy/doc.pdf", "any_bag")

    def test_same_domain_visible(self):
        entry = {"uri": "s3://doc", "domain": "my_bag", "tags": ["internal"]}
        assert _entry_visible(entry, "my_bag")

    def test_different_domain_internal_not_visible(self):
        entry = {"uri": "s3://doc", "domain": "other_bag", "tags": ["internal"]}
        assert not _entry_visible(entry, "my_bag")

    def test_different_domain_public_visible(self):
        entry = {"uri": "s3://doc", "domain": "other_bag", "tags": ["public"]}
        assert _entry_visible(entry, "my_bag")

    def test_empty_tags_same_domain_visible(self):
        entry = {"uri": "s3://doc", "domain": "my_bag", "tags": []}
        assert _entry_visible(entry, "my_bag")

    def test_empty_tags_other_domain_not_visible(self):
        entry = {"uri": "s3://doc", "domain": "other_bag", "tags": []}
        assert not _entry_visible(entry, "my_bag")
