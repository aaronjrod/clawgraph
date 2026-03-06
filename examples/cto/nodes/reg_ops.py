from clawgraph import ClawOutput, Signal, clawnode


@clawnode(
    id="ectd_publisher",
    description="Generates and validates eCTD submission packages.",
    bag="reg_ops",
    skills=["reg_ops/ectd_publishing.md"],
    tools=["pdf_parser"],
    requires=["source_docs"]
)
def publish_ectd(state: dict) -> ClawOutput:
    archive = state.get("document_archive", {})
    if "source_docs" not in archive:
        return ClawOutput(
            signal=Signal.STALLED,
            node_id="ectd_publisher",
            orchestrator_summary="Awaiting source documents for eCTD synthesis.",
        )
    import os
    abs_path = os.path.abspath("examples/cto/artifacts/generated/ectd_package.md")
    return ClawOutput(
        signal=Signal.DONE,
        node_id="ectd_publisher",
        orchestrator_summary="eCTD Package Validated. All 5 modules successfully compiled and verified against regional XML validation criteria.",
        result_uri=f"file://{abs_path}",
    )

@clawnode(
    id="formatting",
    description="Coordinates submission formatting and hyperlinks.",
    bag="reg_ops",
    skills=["reg_ops/formatting_coordination.md"],
    tools=["pdf_parser"],
    requires=["unformatted_modules"]
)
def format_submission(state: dict) -> ClawOutput:
    archive = state.get("document_archive", {})
    if "unformatted_modules" not in archive:
        return ClawOutput(
            signal=Signal.STALLED,
            node_id="formatting",
            orchestrator_summary="Awaiting unformatted module drafts.",
        )
    import os
    abs_path = os.path.abspath("examples/cto/artifacts/generated/formatting.md")
    return ClawOutput(
        signal=Signal.DONE,
        node_id="formatting",
        orchestrator_summary="Formatting & Hyperlinks checked. Corrected 14 broken internal references in Module 3 and applied standard ICH stylesheets.",
        result_uri=f"file://{abs_path}",
    )

@clawnode(
    id="global_coord",
    description="Coordinates global multi-country regulatory filings.",
    bag="reg_ops",
    skills=["reg_ops/global_coordination.md"],
    tools=["gmail_api"],
    requires=["regional_clearance"]
)
def coordinate_global(state: dict) -> ClawOutput:
    archive = state.get("document_archive", {})
    if "regional_clearance" not in archive:
        return ClawOutput(
            signal=Signal.STALLED,
            node_id="global_coord",
            orchestrator_summary="Awaiting regional dispatch clearance.",
        )
    import os
    abs_path = os.path.abspath("examples/cto/artifacts/generated/global_coord.md")
    return ClawOutput(
        signal=Signal.DONE,
        node_id="global_coord",
        orchestrator_summary="Global filing dispatched. EMA and MHRA gateways have confirmed receipt of Sequence 0001.",
        result_uri=f"file://{abs_path}",
    )

@clawnode(
    id="submission_publisher",
    description="Publishes regions submissions into eCTD format.",
    bag="reg_ops",
    requires=["submission_plan"],
)
def publish_submission(state: dict) -> ClawOutput:
    archive = state.get("document_archive", {})
    if "submission_plan" not in archive:
        return ClawOutput(signal=Signal.STALLED, node_id="submission_publisher", orchestrator_summary="Awaiting submission plan.")
    import os
    abs_path = os.path.abspath("examples/cto/artifacts/generated/ectd_sequence_0001.md")
    return ClawOutput(
        signal=Signal.DONE,
        node_id="submission_publisher",
        orchestrator_summary="Compiled EMEA eCTD submission Sequence 0001. Escalating Module 1 translation dependencies to regional vendors to preserve Q4 filing targets.",
        result_uri=f"file://{abs_path}"
    )
