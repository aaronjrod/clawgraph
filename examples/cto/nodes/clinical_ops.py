from clawgraph import ClawOutput, Signal, clawnode
from clawgraph.core.models import HumanRequest

@clawnode(
    id="patient_sync",
    description="Daily patient tracking and timezone synchronization.",
    bag="clinical_ops",
    skills=["clinical_ops/patient_tracking_sync.md"],
    tools=["excel_bridge", "gmail_api"],
)
def sync_patient(state: dict) -> ClawOutput:
    import os
    abs_path = os.path.abspath("examples/cto/artifacts/generated/patient_sync.md")
    return ClawOutput(
        signal=Signal.DONE,
        node_id="patient_sync",
        orchestrator_summary="Daily timezone sync complete. Hint: check new enrollment.",
        result_uri=f"file://{abs_path}",
    )

@clawnode(
    id="onboarding",
    description="Onboards new patients with documentation.",
    bag="clinical_ops",
    skills=["clinical_ops/new_patient_onboarding.md"],
    tools=["gmail_api", "pdf_parser"],
)
def onboard_patient(state: dict) -> ClawOutput:
    import os
    abs_path = os.path.abspath("examples/cto/artifacts/generated/onboarding.md")
    return ClawOutput(
        signal=Signal.DONE,
        node_id="onboarding",
        orchestrator_summary="Docs released to patient, doctor & lab.",
        result_uri=f"file://{abs_path}",
    )

@clawnode(
    id="lab_vetting",
    description="Vets lab invoices against Schedule of Assessments.",
    bag="clinical_ops",
    skills=["clinical_ops/lab_invoice_vetting.md"],
    tools=["pdf_parser", "stats_calc"],
)
def vet_invoices(state: dict) -> ClawOutput:
    import os
    abs_path = os.path.abspath("examples/cto/artifacts/generated/lab_vetting.md")
    return ClawOutput(
        signal=Signal.DONE,
        node_id="lab_vetting",
        orchestrator_summary="Invoices aligned with SoA.",
        result_uri=f"file://{abs_path}",
    )

@clawnode(
    id="dosing_alignment",
    description="Manages drug inventory and dosing narration.",
    bag="clinical_ops",
    skills=["clinical_ops/inventory_management.md"],
    tools=["excel_bridge"],
)
def manage_inventory(state: dict) -> ClawOutput:
    import os
    abs_path = os.path.abspath("examples/cto/artifacts/generated/inventory.md")
    return ClawOutput(
        signal=Signal.DONE,
        node_id="dosing_alignment",
        orchestrator_summary="Inventory synced with dosing narration.",
        result_uri=f"file://{abs_path}",
    )

@clawnode(
    id="deviation_report",
    description="Logs protocol deviations to notary log.",
    bag="clinical_ops",
    skills=["clinical_ops/deviation_reporting.md"],
    tools=["notary_log"],
)
def log_deviation(state: dict) -> ClawOutput:
    import os
    abs_path = os.path.abspath("examples/cto/artifacts/generated/deviation.md")
    return ClawOutput(
        signal=Signal.DONE,
        node_id="deviation_report",
        orchestrator_summary="Deviation indexed.",
        result_uri=f"file://{abs_path}",
    )

@clawnode(
    id="abnormal_triage",
    description="Triages abnormal lab values for physician review.",
    bag="clinical_ops",
    skills=["clinical_ops/abnormality_triage.md"],
    tools=["google_search"],
)
def triage_abnormals(state: dict) -> ClawOutput:
    return ClawOutput(
        signal=Signal.HOLD_FOR_HUMAN,
        node_id="abnormal_triage",
        orchestrator_summary="Mechanism found. Pending Physician sign-off.",
        human_request=HumanRequest(
            message="Abnormal lab value detected. Physician sign-off required.",
            action_type="physician_signoff",
        ),
    )

@clawnode(
    id="integrity_checker",
    description="Cross-dossier entity alignment and NM-class verification.",
    bag="clinical_ops",
    skills=["clinical_ops/document_alignment_checker.md"],
    tools=["pdf_parser"],
)
def check_integrity(state: dict) -> ClawOutput:
    import os
    abs_path = os.path.abspath("examples/cto/artifacts/generated/integrity_check.md")
    return ClawOutput(
        signal=Signal.DONE,
        node_id="integrity_checker",
        orchestrator_summary="Dossier verified.",
        result_uri=f"file://{abs_path}",
    )

@clawnode(
    id="narration_scribe",
    description="Medical scribe narration for patient visits.",
    bag="clinical_ops",
    skills=["clinical_ops/medical_scribe_narration.md"],
    tools=["pdf_parser"],
)
def scribe_visit(state: dict) -> ClawOutput:
    import os
    abs_path = os.path.abspath("examples/cto/artifacts/generated/narration.md")
    return ClawOutput(
        signal=Signal.DONE,
        node_id="narration_scribe",
        orchestrator_summary="Narration complete. Hint: check daily sync.",
        result_uri=f"file://{abs_path}",
    )

@clawnode(
    id="site_activation",
    description="Schedules tracking logistics for clinical trial sites.",
    bag="clinical_ops",
    requires=["feasibility"],
)
def activate_sites(state: dict) -> ClawOutput:
    archive = state.get("document_archive", {})
    if "feasibility" not in archive:
        return ClawOutput(signal=Signal.STALLED, node_id="site_activation", orchestrator_summary="Awaiting feasibility.")
    import os
    abs_path = os.path.abspath("examples/cto/artifacts/generated/site_activation_log.md")
    return ClawOutput(
        signal=Signal.DONE,
        node_id="site_activation",
        orchestrator_summary="Activated primary site (Boston). Fast-tracking Ethics approval for UK site to compensate for anticipated 2-week translation delay.",
        result_uri=f"file://{abs_path}"
    )
