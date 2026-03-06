"""Tests for clawgraph.orchestrator.so_prompts — Super-Orchestrator prompt."""

from clawgraph.orchestrator.so_prompts import build_so_prompt


class TestSOPromptContent:
    def test_contains_identity(self):
        prompt = build_so_prompt(bag_names=["clinical_ops", "reg_ops"])
        assert "Super-Orchestrator" in prompt
        assert "clinical_ops" in prompt
        assert "reg_ops" in prompt

    def test_contains_discovery_first(self):
        prompt = build_so_prompt()
        assert "get_inventory()" in prompt
        assert "Discovery-First" in prompt

    def test_contains_context_discipline(self):
        prompt = build_so_prompt()
        assert "audit_node" in prompt
        assert "summaries only" in prompt

    def test_contains_stalemate_resolution(self):
        prompt = build_so_prompt()
        assert "STALLED" in prompt
        assert "Stalemate" in prompt

    def test_contains_node_design_principles(self):
        prompt = build_so_prompt()
        assert "Single Responsibility" in prompt
        assert "Two-Channel Input" in prompt

    def test_contains_signal_decision_tree(self):
        prompt = build_so_prompt()
        assert "DONE" in prompt
        assert "FAILED" in prompt
        assert "NEED_INTERVENTION" in prompt
        assert "HOLD_FOR_HUMAN" in prompt

    def test_contains_cold_start(self):
        prompt = build_so_prompt()
        assert "Cold-Start" in prompt
        assert "ClawBag" in prompt

    def test_contains_bag_repair(self):
        prompt = build_so_prompt()
        assert "NEED_INTERVENTION" in prompt
        assert "rollback_bag" in prompt

    def test_contains_guardrails(self):
        prompt = build_so_prompt()
        assert "50-node" in prompt or "50 Nodes" in prompt

    def test_empty_bags(self):
        prompt = build_so_prompt(bag_names=[])
        assert "(none yet)" in prompt

    def test_default_bags(self):
        prompt = build_so_prompt()
        assert "(none yet)" in prompt
