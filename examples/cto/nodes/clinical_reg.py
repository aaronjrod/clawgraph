from typing import Any

from clawgraph import ClawOutput, Signal, clawnode
from clawgraph.core.models import HumanRequest

from .llm_utils import run_cto_llm_node


@clawnode(
    id="manage_ind_submission",
    description="Orchestrates the initial IND (Investigational New Drug) submission for global review.",
    bag="clinical_regulatory",
    requires=["protocol_v1"],
    skills=["clinical_reg/protocol_review.md"],
)
def manage_ind_submission(state: dict[str, Any]) -> ClawOutput:
    archive = state.get("document_archive", {})
    if "protocol_v1" not in archive:
        return ClawOutput(
            signal=Signal.HOLD_FOR_HUMAN,
            node_id="manage_ind_submission",
            orchestrator_summary="Awaiting protocol upload.",
        )
    return run_cto_llm_node(
        "manage_ind_submission",
        "Orchestrates the initial IND (Investigational New Drug) submission for global review.",
        state,
        ["clinical_reg/protocol_review.md"],
    )


@clawnode(
    id="protocol_benchmark",
    description="Drafts and benchmarks clinical protocols.",
    bag="clinical_regulatory",
    skills=["clinical_reg/protocol_development.md"],
    tools=["google_search"],
)
def benchmark_protocol(state: dict[str, Any]) -> ClawOutput:
    return run_cto_llm_node(
        "protocol_benchmark",
        "Drafts and benchmarks clinical protocols.",
        state,
        ["clinical_reg/protocol_development.md"],
        tools=["google_search"],
    )


@clawnode(
    id="ib_authoring",
    description="Authors the Investigator's Brochure.",
    bag="clinical_regulatory",
    skills=["clinical_reg/ib_management.md"],
    tools=["pdf_parser", "pubmed_api"],
)
def author_ib(state: dict[str, Any]) -> ClawOutput:
    return run_cto_llm_node(
        "ib_authoring",
        "Authors the Investigator's Brochure.",
        state,
        ["clinical_reg/ib_management.md"],
        tools=["pdf_parser"],
    )


@clawnode(
    id="annual_report",
    description="Generates annual regulatory reports.",
    bag="clinical_regulatory",
    skills=["clinical_reg/annual_reports_meetings.md"],
    tools=["pdf_parser"],
)
def generate_annual_report(state: dict[str, Any]) -> ClawOutput:
    return run_cto_llm_node(
        "annual_report",
        "Generates annual regulatory reports.",
        state,
        ["clinical_reg/annual_reports_meetings.md"],
        tools=["pdf_parser"],
    )


@clawnode(
    id="fda_response_coordinator",
    description="Compiles the Complete Response package when an FDA feedback letter is received.",
    bag="clinical_regulatory",
    requires=["fda_feedback_letter"],
    skills=["clinical_reg/fda_response_coordinator.md"],
    tools=["pdf_parser", "gmail_api"],
)
def coordinate_fda_response(state: dict[str, Any]) -> ClawOutput:
    archive = state.get("document_archive", {})
    if "fda_feedback_letter" not in archive:
        return ClawOutput(
            signal=Signal.NEED_INFO,
            node_id="fda_response_coordinator",
            orchestrator_summary="Paused: Waiting for official FDA response letter.",
            info_request=HumanRequest(
                question="Please upload the formal FDA feedback letter to proceed.",
                context="Clinical hold suspected. Need the exact deficiency list.",
                target="USER",
            ),
        )
    return run_cto_llm_node(
        "fda_response_coordinator",
        "Compiles the Complete Response package when an FDA feedback letter is received.",
        state,
        ["clinical_reg/fda_response_coordinator.md"],
        tools=["pdf_parser", "gmail_api"],
    )
