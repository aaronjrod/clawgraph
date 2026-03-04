"""Smoke test: Register CTO example nodes into bags and verify API compatibility."""

import sys
from pathlib import Path

from clawgraph.bag.manager import BagManager
from clawgraph.core.models import ClawOutput, Signal

# Add examples dir to path so we can import nodes.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "examples" / "cto"))

from nodes import (
    assess_risk,
    author_ib,
    author_mod3,
    benchmark_protocol,
    check_integrity,
    coordinate_global,
    format_submission,
    generate_annual_report,
    log_deviation,
    manage_ccds,
    manage_ind_submission,
    manage_inventory,
    manage_stability,
    negotiate_label,
    onboard_patient,
    publish_ectd,
    scribe_visit,
    sync_patient,
    triage_abnormals,
    validate_process,
    vet_invoices,
    write_pr,
)

# Group nodes by bag for registration.
BAG_NODES = {
    "clinical_regulatory": [
        manage_ind_submission, benchmark_protocol, author_ib, generate_annual_report,
    ],
    "cmc_regulatory": [
        manage_stability, author_mod3, validate_process,
    ],
    "clinical_ops": [
        sync_patient, onboard_patient, vet_invoices, manage_inventory,
        log_deviation, triage_abnormals, check_integrity, scribe_visit,
    ],
    "reg_ops": [
        publish_ectd, format_submission, coordinate_global,
    ],
    "strategy_labeling": [
        assess_risk, negotiate_label, manage_ccds,
    ],
    "marketing": [
        write_pr,
    ],
}


class TestCTONodeRegistration:
    """Verify all 22 CTO nodes can be registered into bags."""

    def test_all_bags_created(self):
        bags = {}
        for bag_name, node_fns in BAG_NODES.items():
            bag = BagManager(name=bag_name)
            for fn in node_fns:
                bag.register_node(fn)
            bags[bag_name] = bag

        assert len(bags) == 6
        total_nodes = sum(len(b) for b in bags.values())
        assert total_nodes == 22

    def test_inventory_returns_tier1(self):
        bag = BagManager(name="clinical_ops")
        for fn in BAG_NODES["clinical_ops"]:
            bag.register_node(fn)
        inv = bag.get_inventory()
        assert inv["node_count"] == 8
        assert "patient_sync" in inv["nodes"]
        assert inv["nodes"]["patient_sync"]["description"] is not None

    def test_node_execution_returns_clawoutput(self):
        """Each node should return a valid ClawOutput."""
        for bag_name, node_fns in BAG_NODES.items():
            for fn in node_fns:
                result = fn({})
                assert isinstance(result, ClawOutput), (
                    f"{fn.__name__} in {bag_name} did not return ClawOutput"
                )

    def test_hold_for_human_node(self):
        """The abnormal_triage node should emit HOLD_FOR_HUMAN with a HumanRequest."""
        result = triage_abnormals({})
        assert result.signal == Signal.HOLD_FOR_HUMAN
        assert result.human_request is not None
        assert "sign-off" in result.human_request.message.lower()

    def test_skills_metadata_present(self):
        """All CTO nodes should have skills in their metadata."""
        for node_fns in BAG_NODES.values():
            for fn in node_fns:
                meta = fn._clawnode_metadata
                assert len(meta.skills) > 0, (
                    f"{fn.__name__} has no skills"
                )
