from clawgraph import ClawOutput, Signal, clawnode

@clawnode(
    id="risk_assess",
    description="Assesses market risk for regulatory strategy.",
    bag="strategy_labeling",
    skills=["strategy/risk_negotiation.md"],
    tools=["google_search"],
    requires=["clinical_data"]
)
def assess_risk(state: dict) -> ClawOutput:
    archive = state.get("document_archive", {})
    if "clinical_data" not in archive:
        return ClawOutput(
            signal=Signal.STALLED,
            node_id="risk_assess",
            orchestrator_summary="Awaiting clinical endpoint data for risk quantification.",
        )
    import os
    abs_path = os.path.abspath("examples/cto/artifacts/generated/risk_assessment.md")
    return ClawOutput(
        signal=Signal.DONE,
        node_id="risk_assess",
        orchestrator_summary="Market risk assessed. Hepatic safety signals pose a moderate labeling risk; recommending proactive REMS proposal drafting.",
        result_uri=f"file://{abs_path}",
    )

@clawnode(
    id="label_negotiator",
    description="Optimizes USPI labeling strategy.",
    bag="strategy_labeling",
    skills=["strategy/approval_strategy.md"],
    tools=["pdf_parser"],
    requires=["preliminary_label"]
)
def negotiate_label(state: dict) -> ClawOutput:
    archive = state.get("document_archive", {})
    if "preliminary_label" not in archive:
        return ClawOutput(
            signal=Signal.STALLED,
            node_id="label_negotiator",
            orchestrator_summary="Awaiting preliminary label drafting.",
        )
    import os
    abs_path = os.path.abspath("examples/cto/artifacts/generated/label_negotiation.md")
    return ClawOutput(
        signal=Signal.DONE,
        node_id="label_negotiator",
        orchestrator_summary="USPI optimization draft ready. Strengthened the efficacy claims in Section 14 while balancing the newly proposed black box warning.",
        result_uri=f"file://{abs_path}",
    )

@clawnode(
    id="ccds_manager",
    description="Aligns CCDS with safety signals across regions.",
    bag="strategy_labeling",
    skills=["labeling/leaflets_ccds.md"],
    tools=["pdf_parser"],
    requires=["safety_signals"]
)
def manage_ccds(state: dict) -> ClawOutput:
    archive = state.get("document_archive", {})
    if "safety_signals" not in archive:
        return ClawOutput(
            signal=Signal.STALLED,
            node_id="ccds_manager",
            orchestrator_summary="Awaiting global safety signal alignments.",
        )
    import os
    abs_path = os.path.abspath("examples/cto/artifacts/generated/ccds.md")
    return ClawOutput(
        signal=Signal.DONE,
        node_id="ccds_manager",
        orchestrator_summary="CCDS updated. Integrated Q2 spontaneous thrombocytopenia reports; no core safety info changes required.",
        result_uri=f"file://{abs_path}",
    )
