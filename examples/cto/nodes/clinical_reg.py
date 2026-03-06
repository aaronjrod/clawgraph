from clawgraph import ClawOutput, Signal, clawnode
from clawgraph.bag.patterns import DocumentNode
from clawgraph.core.models import HumanRequest


@clawnode(
    id="manage_ind_submission",
    description="Orchestrates the initial IND (Investigational New Drug) submission for global review.",
    bag="clinical_regulatory",
    requires=["protocol_v1"],
    skills=["clinical_reg/protocol_review.md"]
)
def manage_ind_submission(state: dict) -> ClawOutput:
    dn = DocumentNode("manage_ind_submission")
    archive = state.get("document_archive", {})
    import os
    abs_path = os.path.abspath("examples/cto/artifacts/generated/ind-package-v1.md")

    if "protocol_v1" not in archive:
        return dn.create(
            uri=f"file://{abs_path}",
            summary="Created initial IND shell. Awaiting protocol upload."
        )

    return dn.read(
        finding="Protocol v1 confirmed. Methodology section requires clarification on sample size N=450 justification.",
        uri=f"file://{abs_path}"
    )

@clawnode(
    id="protocol_benchmark",
    description="Drafts and benchmarks clinical protocols.",
    bag="clinical_regulatory",
    skills=["clinical_reg/protocol_development.md"],
    tools=["google_search"],
)
def benchmark_protocol(state: dict) -> ClawOutput:
    import os
    abs_path = os.path.abspath("examples/cto/artifacts/generated/protocol_draft.md")
    return ClawOutput(
        signal=Signal.DONE,
        node_id="protocol_benchmark",
        orchestrator_summary="Drafted core protocol (v1.0). Aligned inclusion/exclusion criteria against competitive Phase 2 trials. Proceeding to statistical power validation.",
        result_uri=f"file://{abs_path}",
    )

@clawnode(
    id="ib_authoring",
    description="Authors the Investigator's Brochure.",
    bag="clinical_regulatory",
    skills=["clinical_reg/ib_management.md"],
    tools=["pdf_parser", "pubmed_api"],
)
def author_ib(state: dict) -> ClawOutput:
    import os
    abs_path = os.path.abspath("examples/cto/artifacts/generated/ib_section7.md")
    return ClawOutput(
        signal=Signal.DONE,
        node_id="ib_authoring",
        orchestrator_summary="Successfully authored Investigator's Brochure Section 7. Consolidated the latest preclinical safety pharmacology data to justify human dosage limits in upcoming trials.",
        result_uri=f"file://{abs_path}",
    )

@clawnode(
    id="annual_report",
    description="Generates annual regulatory reports.",
    bag="clinical_regulatory",
    skills=["clinical_reg/annual_reports_meetings.md"],
    tools=["pdf_parser"],
)
def generate_annual_report(state: dict) -> ClawOutput:
    import os
    abs_path = os.path.abspath("examples/cto/artifacts/generated/annual_report.md")
    return ClawOutput(
        signal=Signal.DONE,
        node_id="annual_report",
        orchestrator_summary="Compiled the Annual Regulatory Report (DSUR). Assessed global adverse events across all sites and confirmed the overall risk-benefit ratio remains positive.",
        result_uri=f"file://{abs_path}",
    )

@clawnode(
    id="fda_response_coordinator",
    description="Compiles the Complete Response package when an FDA feedback letter is received.",
    bag="clinical_regulatory",
    requires=["fda_feedback_letter"],
    skills=["clinical_reg/fda_response_coordinator.md"],
    tools=["pdf_parser", "gmail_api"],
)
def coordinate_fda_response(state: dict) -> ClawOutput:
    archive = state.get("document_archive", {})
    if "fda_feedback_letter" not in archive:
        return ClawOutput(
            signal=Signal.NEED_INFO,
            node_id="fda_response_coordinator",
            orchestrator_summary="Paused: Waiting for official FDA response letter.",
            info_request=HumanRequest(
                question="Please upload the formal FDA feedback letter to proceed.",
                context="Clinical hold suspected. Need the exact deficiency list.",
                target="USER"
            )
        )

    import os
    abs_path = os.path.abspath("examples/cto/artifacts/generated/fda_response_v1.md")
    return ClawOutput(
        signal=Signal.DONE,
        node_id="fda_response_coordinator",
        orchestrator_summary="Complete Response Package compiled and sent for QA.",
        result_uri=f"file://{abs_path}",
    )
