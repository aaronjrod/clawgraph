from typing import Any

from clawgraph import ClawOutput, Signal, clawnode
from clawgraph.core.models import HumanRequest

from .llm_utils import run_cto_llm_node


@clawnode(
    id="ectd_publisher",
    description="Generates and validates eCTD submission packages.",
    bag="reg_ops",
    skills=["reg_ops/ectd_publishing.md"],
    tools=["pdf_parser"],
    requires=["source_docs"],
)
def publish_ectd(state: dict[str, Any]) -> ClawOutput:
    archive = state.get("document_archive", {})
    if "source_docs" not in archive:
        return ClawOutput(
            signal=Signal.HOLD_FOR_HUMAN,
            node_id="ectd_publisher",
            orchestrator_summary="Awaiting source documents for eCTD synthesis.",
            human_request=HumanRequest(message="Awaiting source documents for eCTD synthesis."),
        )
    return run_cto_llm_node(
        node_id="ectd_publisher",
        description="Generates and validates eCTD submission packages.",
        state=state,
        skills=["reg_ops/ectd_publishing.md"],
    )


@clawnode(
    id="formatting",
    description="Coordinates submission formatting and hyperlinks.",
    bag="reg_ops",
    skills=["reg_ops/formatting_coordination.md"],
    tools=["pdf_parser"],
    requires=["unformatted_modules"],
)
def format_submission(state: dict[str, Any]) -> ClawOutput:
    archive = state.get("document_archive", {})
    if "unformatted_modules" not in archive:
        return ClawOutput(
            signal=Signal.HOLD_FOR_HUMAN,
            node_id="formatting",
            orchestrator_summary="Awaiting unformatted module drafts.",
            human_request=HumanRequest(message="Awaiting unformatted module drafts."),
        )
    return run_cto_llm_node(
        node_id="formatting",
        description="Coordinates submission formatting and hyperlinks.",
        state=state,
        skills=["reg_ops/formatting_coordination.md"],
    )


@clawnode(
    id="global_coord",
    description="Coordinates global multi-country regulatory filings.",
    bag="reg_ops",
    skills=["reg_ops/global_coordination.md"],
    tools=["gmail_api"],
    requires=["regional_clearance"],
)
def coordinate_global(state: dict[str, Any]) -> ClawOutput:
    archive = state.get("document_archive", {})
    if "regional_clearance" not in archive:
        return ClawOutput(
            signal=Signal.HOLD_FOR_HUMAN,
            node_id="global_coord",
            orchestrator_summary="Awaiting regional dispatch clearance.",
            human_request=HumanRequest(message="Awaiting regional dispatch clearance."),
        )
    return run_cto_llm_node(
        node_id="global_coord",
        description="Coordinates global multi-country regulatory filings.",
        state=state,
        skills=["reg_ops/global_coordination.md"],
    )


@clawnode(
    id="submission_publisher",
    description="Publishes regions submissions into eCTD format.",
    bag="reg_ops",
    requires=["submission_plan"],
)
def publish_submission(state: dict[str, Any]) -> ClawOutput:
    archive = state.get("document_archive", {})
    if "submission_plan" not in archive:
        return ClawOutput(
            signal=Signal.HOLD_FOR_HUMAN,
            node_id="submission_publisher",
            orchestrator_summary="Awaiting submission plan.",
        )
    return run_cto_llm_node(
        node_id="submission_publisher",
        description="Publishes regions submissions into eCTD format.",
        state=state,
        skills=[],
    )
