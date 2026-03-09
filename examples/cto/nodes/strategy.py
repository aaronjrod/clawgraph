from typing import Any

from clawgraph import ClawOutput, Signal, clawnode
from clawgraph.core.models import HumanRequest

from .llm_utils import run_cto_llm_node


@clawnode(
    id="risk_assess",
    description="Assesses market risk for regulatory strategy.",
    bag="strategy_labeling",
    skills=["strategy/risk_negotiation.md"],
    tools=["google_search"],
    requires=["clinical_data"],
)
def assess_risk(state: dict[str, Any]) -> ClawOutput:
    archive = state.get("document_archive", {})
    if "clinical_data" not in archive:
        return ClawOutput(
            signal=Signal.HOLD_FOR_HUMAN,
            node_id="risk_assess",
            orchestrator_summary="Awaiting clinical endpoint data for risk quantification.",
            human_request=HumanRequest(
                message="Awaiting clinical endpoint data for risk quantification."
            ),
        )
    return run_cto_llm_node(
        node_id="risk_assess",
        description="Assesses market risk for regulatory strategy.",
        state=state,
        skills=["strategy/risk_negotiation.md"],
    )


@clawnode(
    id="label_negotiator",
    description="Optimizes USPI labeling strategy.",
    bag="strategy_labeling",
    skills=["strategy/approval_strategy.md"],
    tools=["pdf_parser"],
    requires=["preliminary_label"],
)
def negotiate_label(state: dict[str, Any]) -> ClawOutput:
    archive = state.get("document_archive", {})
    if "preliminary_label" not in archive:
        return ClawOutput(
            signal=Signal.HOLD_FOR_HUMAN,
            node_id="label_negotiator",
            orchestrator_summary="Awaiting preliminary label drafting.",
            human_request=HumanRequest(message="Awaiting preliminary label drafting."),
        )
    return run_cto_llm_node(
        node_id="label_negotiator",
        description="Optimizes USPI labeling strategy.",
        state=state,
        skills=["strategy/approval_strategy.md"],
    )


@clawnode(
    id="ccds_manager",
    description="Aligns CCDS with safety signals across regions.",
    bag="strategy_labeling",
    skills=["labeling/leaflets_ccds.md"],
    tools=["pdf_parser"],
    requires=["safety_signals"],
)
def manage_ccds(state: dict[str, Any]) -> ClawOutput:
    archive = state.get("document_archive", {})
    if "safety_signals" not in archive:
        return ClawOutput(
            signal=Signal.HOLD_FOR_HUMAN,
            node_id="ccds_manager",
            orchestrator_summary="Awaiting global safety signal alignments.",
            human_request=HumanRequest(message="Awaiting global safety signal alignments."),
        )
    return run_cto_llm_node(
        node_id="ccds_manager",
        description="Aligns CCDS with safety signals across regions.",
        state=state,
        skills=["labeling/leaflets_ccds.md"],
    )
