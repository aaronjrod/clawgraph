from clawgraph import ClawOutput, Signal, clawnode
from clawgraph.core.models import HumanRequest
from .llm_utils import run_cto_llm_node

@clawnode(
    id="press_writer",
    description="Drafts press releases for regulatory milestones.",
    bag="marketing",
    skills=["marketing/press_release.md"],
    tools=["gmail_api"],
    requires=["milestone_confirmation"]
)
def write_pr(state: dict) -> ClawOutput:
    archive = state.get("document_archive", {})
    if "milestone_confirmation" not in archive:
        return ClawOutput(
            signal=Signal.HOLD_FOR_HUMAN,
            node_id="press_writer",
            orchestrator_summary="Awaiting regulatory milestone confirmation.",
            human_request=HumanRequest(message="Awaiting regulatory milestone confirmation."),
        )
    return run_cto_llm_node(
        node_id="press_writer",
        description="Drafts press releases for regulatory milestones.",
        state=state,
        skills=["marketing/press_release.md"]
    )
