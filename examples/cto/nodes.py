"""
ClawGraph Expert Example: Clinical Trial Operations (CTO)
Architecture: One Bag Per Specialist | One Node Per Task | Explicit Tool Authorization
"""

from clawgraph import clawnode, ClawOutput, Signal
from clawgraph.core.models import HumanRequest

# --- Specialist Tools (Mock Imports) ---
# Each bag is authorized for specific tools defined in examples/cto/tools/
# from tools.google_search import GoogleSearch
# from tools.pdf_parser import PDFParser
# from tools.excel_bridge import ExcelBridge
# from tools.stats_calc import StatsCalc
# from tools.gmail_api import GmailAPI
# from tools.notary_log import NotaryLog

# --- BAG 1: Clinical_Regulatory_Bag ---


@clawnode(
    id="ind_submission",
    description="Compiles IND submission packages.",
    bag="clinical_regulatory",
    skills=["clinical_reg/ind_submissions.md"],
    tools=["pdf_parser"],
)
def manage_ind_submission(state: dict) -> ClawOutput:
    return ClawOutput(
        signal=Signal.DONE,
        node_id="ind_submission",
        orchestrator_summary="IND Package Prepared.",
        result_uri="uri://clinical_regulatory/ind_package.json",
    )


@clawnode(
    id="protocol_benchmark",
    description="Drafts and benchmarks clinical protocols.",
    bag="clinical_regulatory",
    skills=["clinical_reg/protocol_development.md"],
    tools=["google_search"],
)
def benchmark_protocol(state: dict) -> ClawOutput:
    return ClawOutput(
        signal=Signal.DONE,
        node_id="protocol_benchmark",
        orchestrator_summary="Protocol drafted. Hint: check CMC alignment.",
        result_uri="uri://clinical_regulatory/protocol_draft.json",
    )


@clawnode(
    id="ib_authoring",
    description="Authors Investigator Brochure sections.",
    bag="clinical_regulatory",
    skills=["clinical_reg/investigator_brochure.md"],
    tools=["stats_calc"],
)
def author_ib(state: dict) -> ClawOutput:
    return ClawOutput(
        signal=Signal.DONE,
        node_id="ib_authoring",
        orchestrator_summary="IB Section 7 updated.",
        result_uri="uri://clinical_regulatory/ib_section7.json",
    )


@clawnode(
    id="annual_report",
    description="Generates annual regulatory reports.",
    bag="clinical_regulatory",
    skills=["clinical_reg/annual_reports_meetings.md"],
    tools=["pdf_parser"],
)
def generate_annual_report(state: dict) -> ClawOutput:
    return ClawOutput(
        signal=Signal.DONE,
        node_id="annual_report",
        orchestrator_summary="Annual Report drafted.",
        result_uri="uri://clinical_regulatory/annual_report.json",
    )


# --- BAG 2: CMC_Regulatory_Bag ---


@clawnode(
    id="stability_manager",
    description="Monitors stability data and impurity drift.",
    bag="cmc_regulatory",
    skills=["cmc_reg/stability_data_management.md"],
    tools=["excel_bridge", "stats_calc"],
)
def manage_stability(state: dict) -> ClawOutput:
    return ClawOutput(
        signal=Signal.DONE,
        node_id="stability_manager",
        orchestrator_summary="Stability trends within 0.1%. Hint: check IND annual update.",
        result_uri="uri://cmc_regulatory/stability_trends.json",
    )


@clawnode(
    id="mod3_author",
    description="Authors Module 3 technical documentation.",
    bag="cmc_regulatory",
    skills=["cmc_reg/module_3_authoring.md"],
    tools=["pdf_parser"],
)
def author_mod3(state: dict) -> ClawOutput:
    return ClawOutput(
        signal=Signal.DONE,
        node_id="mod3_author",
        orchestrator_summary="Module 3 updated.",
        result_uri="uri://cmc_regulatory/module3.json",
    )


@clawnode(
    id="process_val",
    description="Validates drug substance manufacturing processes.",
    bag="cmc_regulatory",
    skills=["cmc_reg/drug_substance_process_validation.md"],
    tools=["stats_calc"],
)
def validate_process(state: dict) -> ClawOutput:
    return ClawOutput(
        signal=Signal.DONE,
        node_id="process_val",
        orchestrator_summary="Manufacturing comparability confirmed.",
        result_uri="uri://cmc_regulatory/process_validation.json",
    )


# --- BAG 3: Clinical_Ops_Bag (The "Daily Heartbeat") ---


@clawnode(
    id="patient_sync",
    description="Daily patient tracking and timezone synchronization.",
    bag="clinical_ops",
    skills=["clinical_ops/patient_tracking_sync.md"],
    tools=["excel_bridge", "gmail_api"],
)
def sync_patient(state: dict) -> ClawOutput:
    return ClawOutput(
        signal=Signal.DONE,
        node_id="patient_sync",
        orchestrator_summary="Daily timezone sync complete. Hint: check new enrollment.",
        result_uri="uri://clinical_ops/patient_sync.json",
    )


@clawnode(
    id="onboarding",
    description="Onboards new patients with documentation.",
    bag="clinical_ops",
    skills=["clinical_ops/new_patient_onboarding.md"],
    tools=["gmail_api", "pdf_parser"],
)
def onboard_patient(state: dict) -> ClawOutput:
    return ClawOutput(
        signal=Signal.DONE,
        node_id="onboarding",
        orchestrator_summary="Docs released to patient, doctor & lab.",
        result_uri="uri://clinical_ops/onboarding.json",
    )


@clawnode(
    id="lab_vetting",
    description="Vets lab invoices against Schedule of Assessments.",
    bag="clinical_ops",
    skills=["clinical_ops/lab_invoice_vetting.md"],
    tools=["pdf_parser", "stats_calc"],
)
def vet_invoices(state: dict) -> ClawOutput:
    return ClawOutput(
        signal=Signal.DONE,
        node_id="lab_vetting",
        orchestrator_summary="Invoices aligned with SoA.",
        result_uri="uri://clinical_ops/lab_vetting.json",
    )


@clawnode(
    id="dosing_alignment",
    description="Manages drug inventory and dosing narration.",
    bag="clinical_ops",
    skills=["clinical_ops/inventory_management.md"],
    tools=["excel_bridge"],
)
def manage_inventory(state: dict) -> ClawOutput:
    return ClawOutput(
        signal=Signal.DONE,
        node_id="dosing_alignment",
        orchestrator_summary="Inventory synced with dosing narration.",
        result_uri="uri://clinical_ops/inventory.json",
    )


@clawnode(
    id="deviation_report",
    description="Logs protocol deviations to notary log.",
    bag="clinical_ops",
    skills=["clinical_ops/deviation_reporting.md"],
    tools=["notary_log"],
)
def log_deviation(state: dict) -> ClawOutput:
    return ClawOutput(
        signal=Signal.DONE,
        node_id="deviation_report",
        orchestrator_summary="Deviation indexed.",
        result_uri="uri://clinical_ops/deviation.json",
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
    return ClawOutput(
        signal=Signal.DONE,
        node_id="integrity_checker",
        orchestrator_summary="Dossier verified.",
        result_uri="uri://clinical_ops/integrity_check.json",
    )


@clawnode(
    id="narration_scribe",
    description="Medical scribe narration for patient visits.",
    bag="clinical_ops",
    skills=["clinical_ops/medical_scribe_narration.md"],
    tools=["pdf_parser"],
)
def scribe_visit(state: dict) -> ClawOutput:
    return ClawOutput(
        signal=Signal.DONE,
        node_id="narration_scribe",
        orchestrator_summary="Narration complete. Hint: check daily sync.",
        result_uri="uri://clinical_ops/narration.json",
    )


# --- BAG 4: Reg_Ops_Bag ---


@clawnode(
    id="ectd_publisher",
    description="Generates and validates eCTD submission packages.",
    bag="reg_ops",
    skills=["reg_ops/ectd_publishing.md"],
    tools=["pdf_parser"],
)
def publish_ectd(state: dict) -> ClawOutput:
    return ClawOutput(
        signal=Signal.DONE,
        node_id="ectd_publisher",
        orchestrator_summary="eCTD Package Validated.",
        result_uri="uri://reg_ops/ectd_package.json",
    )


@clawnode(
    id="formatting",
    description="Coordinates submission formatting and hyperlinks.",
    bag="reg_ops",
    skills=["reg_ops/formatting_coordination.md"],
    tools=["pdf_parser"],
)
def format_submission(state: dict) -> ClawOutput:
    return ClawOutput(
        signal=Signal.DONE,
        node_id="formatting",
        orchestrator_summary="Formatting & Hyperlinks checked.",
        result_uri="uri://reg_ops/formatting.json",
    )


@clawnode(
    id="global_coord",
    description="Coordinates global multi-country regulatory filings.",
    bag="reg_ops",
    skills=["reg_ops/global_coordination.md"],
    tools=["gmail_api"],
)
def coordinate_global(state: dict) -> ClawOutput:
    return ClawOutput(
        signal=Signal.DONE,
        node_id="global_coord",
        orchestrator_summary="Global filing ready.",
        result_uri="uri://reg_ops/global_coord.json",
    )


# --- BAG 5: Strategy_Labeling_Bag ---


@clawnode(
    id="risk_assess",
    description="Assesses market risk for regulatory strategy.",
    bag="strategy_labeling",
    skills=["strategy/risk_negotiation.md"],
    tools=["google_search"],
)
def assess_risk(state: dict) -> ClawOutput:
    return ClawOutput(
        signal=Signal.DONE,
        node_id="risk_assess",
        orchestrator_summary="Market risk assessed.",
        result_uri="uri://strategy/risk_assessment.json",
    )


@clawnode(
    id="label_negotiator",
    description="Optimizes USPI labeling strategy.",
    bag="strategy_labeling",
    skills=["strategy/approval_strategy.md"],
    tools=["pdf_parser"],
)
def negotiate_label(state: dict) -> ClawOutput:
    return ClawOutput(
        signal=Signal.DONE,
        node_id="label_negotiator",
        orchestrator_summary="USPI optimization draft ready.",
        result_uri="uri://strategy/label_negotiation.json",
    )


@clawnode(
    id="ccds_manager",
    description="Aligns CCDS with safety signals across regions.",
    bag="strategy_labeling",
    skills=["labeling/leaflets_ccds.md"],
    tools=["pdf_parser"],
)
def manage_ccds(state: dict) -> ClawOutput:
    return ClawOutput(
        signal=Signal.DONE,
        node_id="ccds_manager",
        orchestrator_summary="CCDS aligned with Safety Signals.",
        result_uri="uri://strategy/ccds.json",
    )


# --- BAG 6: Marketing_Bag ---


@clawnode(
    id="press_writer",
    description="Drafts press releases for regulatory milestones.",
    bag="marketing",
    skills=["marketing/press_release.md"],
    tools=["gmail_api"],
)
def write_pr(state: dict) -> ClawOutput:
    return ClawOutput(
        signal=Signal.DONE,
        node_id="press_writer",
        orchestrator_summary="Press Release drafted.",
        result_uri="uri://marketing/press_release.json",
    )
