from clawgraph import ClawOutput, Signal, clawnode

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
            signal=Signal.STALLED,
            node_id="press_writer",
            orchestrator_summary="Awaiting regulatory milestone confirmation.",
        )
    import os
    abs_path = os.path.abspath("examples/cto/artifacts/generated/press_release.md")
    return ClawOutput(
        signal=Signal.DONE,
        node_id="press_writer",
        orchestrator_summary="Press Release drafted. Headline approved: 'FDA Accepts IND for Novel CG-204 Therapeutics'. Ready for investor relations review.",
        result_uri=f"file://{abs_path}",
    )
