from typing import Any

from clawgraph import ClawOutput, Signal, clawnode

from .llm_utils import run_cto_llm_node


@clawnode(
    id="patient_sync",
    description="Daily patient tracking and timezone synchronization.",
    bag="clinical_ops",
    skills=["clinical_ops/patient_tracking_sync.md"],
    tools=["excel_bridge", "gmail_api"],
)
def sync_patient(state: dict[str, Any]) -> ClawOutput:
    return run_cto_llm_node(
        "patient_sync",
        "Daily patient tracking and timezone synchronization.",
        state,
        ["clinical_ops/patient_tracking_sync.md"],
    )


@clawnode(
    id="onboarding",
    description="Onboards new patients with documentation.",
    bag="clinical_ops",
    skills=["clinical_ops/new_patient_onboarding.md"],
    tools=["gmail_api", "pdf_parser"],
)
def onboard_patient(state: dict[str, Any]) -> ClawOutput:
    return run_cto_llm_node(
        "onboarding",
        "Onboards new patients with documentation.",
        state,
        ["clinical_ops/new_patient_onboarding.md"],
    )


@clawnode(
    id="lab_vetting",
    description="Vets lab invoices against Schedule of Assessments.",
    bag="clinical_ops",
    skills=["clinical_ops/lab_invoice_vetting.md"],
    tools=["pdf_parser", "stats_calc"],
)
def vet_invoices(state: dict[str, Any]) -> ClawOutput:
    return run_cto_llm_node(
        "lab_vetting",
        "Vets lab invoices against Schedule of Assessments.",
        state,
        ["clinical_ops/lab_invoice_vetting.md"],
    )


@clawnode(
    id="dosing_alignment",
    description="Manages drug inventory and dosing narration.",
    bag="clinical_ops",
    skills=["clinical_ops/inventory_management.md"],
    tools=["excel_bridge"],
)
def manage_inventory(state: dict[str, Any]) -> ClawOutput:
    return run_cto_llm_node(
        "dosing_alignment",
        "Manages drug inventory and dosing narration.",
        state,
        ["clinical_ops/inventory_management.md"],
    )


@clawnode(
    id="deviation_report",
    description="Logs protocol deviations to notary log.",
    bag="clinical_ops",
    skills=["clinical_ops/deviation_reporting.md"],
    tools=["notary_log"],
)
def log_deviation(state: dict[str, Any]) -> ClawOutput:
    return run_cto_llm_node(
        "deviation_report",
        "Logs protocol deviations to notary log.",
        state,
        ["clinical_ops/deviation_reporting.md"],
    )


@clawnode(
    id="abnormal_triage",
    description="Triages abnormal lab values for physician review.",
    bag="clinical_ops",
    skills=["clinical_ops/abnormality_triage.md"],
    tools=["google_search"],
)
def triage_abnormals(state: dict[str, Any]) -> ClawOutput:
    return run_cto_llm_node(
        "abnormal_triage",
        "Triages abnormal lab values for physician review.",
        state,
        ["clinical_ops/abnormality_triage.md"],
    )


@clawnode(
    id="integrity_checker",
    description="Cross-dossier entity alignment and NM-class verification.",
    bag="clinical_ops",
    skills=["clinical_ops/document_alignment_checker.md"],
    tools=["pdf_parser"],
)
def check_integrity(state: dict[str, Any]) -> ClawOutput:
    return run_cto_llm_node(
        "integrity_checker",
        "Cross-dossier entity alignment and NM-class verification.",
        state,
        ["clinical_ops/document_alignment_checker.md"],
    )


@clawnode(
    id="narration_scribe",
    description="Medical scribe narration for patient visits.",
    bag="clinical_ops",
    skills=["clinical_ops/medical_scribe_narration.md"],
    tools=["pdf_parser"],
)
def scribe_visit(state: dict[str, Any]) -> ClawOutput:
    return run_cto_llm_node(
        "narration_scribe",
        "Medical scribe narration for patient visits.",
        state,
        ["clinical_ops/medical_scribe_narration.md"],
    )


@clawnode(
    id="site_activation",
    description="Schedules tracking logistics for clinical trial sites.",
    bag="clinical_ops",
    requires=["feasibility"],
)
def activate_sites(state: dict[str, Any]) -> ClawOutput:
    archive = state.get("document_archive", {})
    if "feasibility" not in archive:
        return ClawOutput(
            signal=Signal.HOLD_FOR_HUMAN,
            node_id="site_activation",
            orchestrator_summary="Awaiting feasibility.",
        )
    return run_cto_llm_node(
        "site_activation", "Schedules tracking logistics for clinical trial sites.", state, []
    )
