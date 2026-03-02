"""
ClawGraph Expert Example: Clinical Trial Operations (CTO)
Architecture: One Bag Per Specialist | One Node Per Task | Explicit Tool Authorization
"""

from clawgraph import clawnode, ClawOutput, Signal

# --- Specialist Tools (Mock Imports) ---
# Each bag is authorized for specific tools defined in examples/cto/tools/
# from tools.google_search import GoogleSearch
# from tools.pdf_parser import PDFParser
# from tools.excel_bridge import ExcelBridge
# from tools.stats_calc import StatsCalc
# from tools.gmail_api import GmailAPI
# from tools.notary_log import NotaryLog

# --- BAG 1: Clinical_Regulatory_Bag ---

@clawnode(id="ind_submission", bag="clinical_regulatory", skills=["clinical_reg/ind_submissions.md"], tools=["pdf_parser"])
def manage_ind_submission(inputs: dict) -> ClawOutput:
    return ClawOutput(signal=Signal.DONE, summary="IND Package Prepared.")

@clawnode(id="protocol_benchmark", bag="clinical_regulatory", skills=["clinical_reg/protocol_development.md"], tools=["google_search"])
def benchmark_protocol(inputs: dict) -> ClawOutput:
    return ClawOutput(signal=Signal.DONE, summary="Protocol drafted.", next_steps_hint=["trigger:cmc_alignment"])

@clawnode(id="ib_authoring", bag="clinical_regulatory", skills=["clinical_reg/investigator_brochure.md"], tools=["stats_calc"])
def author_ib(inputs: dict) -> ClawOutput:
    return ClawOutput(signal=Signal.DONE, summary="IB Section 7 updated.")

@clawnode(id="annual_report", bag="clinical_regulatory", skills=["clinical_reg/annual_reports_meetings.md"], tools=["pdf_parser"])
def generate_annual_report(inputs: dict) -> ClawOutput:
    return ClawOutput(signal=Signal.DONE, summary="Annual Report drafted.")

# --- BAG 2: CMC_Regulatory_Bag ---

@clawnode(id="stability_manager", bag="cmc_regulatory", skills=["cmc_reg/stability_data_management.md"], tools=["excel_bridge", "stats_calc"])
def manage_stability(inputs: dict) -> ClawOutput:
    return ClawOutput(signal=Signal.DONE, summary="Stability trends within 0.1%.", next_steps_hint=["trigger:ind_annual_update"])

@clawnode(id="mod3_author", bag="cmc_regulatory", skills=["cmc_reg/module_3_authoring.md"], tools=["pdf_parser"])
def author_mod3(inputs: dict) -> ClawOutput:
    return ClawOutput(signal=Signal.DONE, summary="Module 3 updated.")

@clawnode(id="process_val", bag="cmc_regulatory", skills=["cmc_reg/drug_substance_process_validation.md"], tools=["stats_calc"])
def validate_process(inputs: dict) -> ClawOutput:
    return ClawOutput(signal=Signal.DONE, summary="Manufacturing comparability confirmed.")

# --- BAG 3: Clinical_Ops_Bag (The "Daily Heartbeat") ---

@clawnode(id="patient_sync", bag="clinical_ops", skills=["clinical_ops/patient_tracking_sync.md"], tools=["excel_bridge", "gmail_api"])
def sync_patient(inputs: dict) -> ClawOutput:
    return ClawOutput(signal=Signal.DONE, summary="Daily timezone sync complete.", next_steps_hint=["check:new_enrollment"])

@clawnode(id="onboarding", bag="clinical_ops", skills=["clinical_ops/new_patient_onboarding.md"], tools=["gmail_api", "pdf_parser"])
def onboard_patient(inputs: dict) -> ClawOutput:
    return ClawOutput(signal=Signal.DONE, summary="Docs released to patient, doctor & lab.")

@clawnode(id="lab_vetting", bag="clinical_ops", skills=["clinical_ops/lab_invoice_vetting.md"], tools=["pdf_parser", "stats_calc"])
def vet_invoices(inputs: dict) -> ClawOutput:
    return ClawOutput(signal=Signal.DONE, summary="Invoices aligned with SoA.")

@clawnode(id="dosing_alignment", bag="clinical_ops", skills=["clinical_ops/inventory_management.md"], tools=["excel_bridge"])
def manage_inventory(inputs: dict) -> ClawOutput:
    return ClawOutput(signal=Signal.DONE, summary="Inventory synced with dosing naration.")

@clawnode(id="deviation_report", bag="clinical_ops", skills=["clinical_ops/deviation_reporting.md"], tools=["notary_log"])
def log_deviation(inputs: dict) -> ClawOutput:
    return ClawOutput(signal=Signal.DONE, summary="Deviation indexed.")

@clawnode(id="abnormal_triage", bag="clinical_ops", skills=["clinical_ops/abnormality_triage.md"], tools=["google_search"])
def triage_abnormals(inputs: dict) -> ClawOutput:
    return ClawOutput(signal=Signal.HOLD_FOR_HUMAN, summary="Mechanism found. Pending Physician sign-off.")

@clawnode(id="integrity_checker", bag="clinical_ops", skills=["clinical_ops/document_alignment_checker.md"], tools=["pdf_parser"])
def check_integrity(inputs: dict) -> ClawOutput:
    # CATCHING THE NM5072 vs NM5082 TRAP
    return ClawOutput(signal=Signal.DONE, summary="Dossier verified.")

@clawnode(id="narration_scribe", bag="clinical_ops", skills=["clinical_ops/medical_scribe_narration.md"], tools=["pdf_parser"])
def scribe_visit(inputs: dict) -> ClawOutput:
    return ClawOutput(signal=Signal.DONE, summary="Narration complete.", next_steps_hint=["trigger:daily_sync"])

# --- BAG 4: Reg_Ops_Bag ---

@clawnode(id="ectd_publisher", bag="reg_ops", skills=["reg_ops/ectd_publishing.md"], tools=["pdf_parser"])
def publish_ectd(inputs: dict) -> ClawOutput:
    return ClawOutput(signal=Signal.DONE, summary="eCTD Package Validated.")

@clawnode(id="formatting", bag="reg_ops", skills=["reg_ops/formatting_coordination.md"], tools=["pdf_parser"])
def format_submission(inputs: dict) -> ClawOutput:
    return ClawOutput(signal=Signal.DONE, summary="Formatting & Hyperlinks checked.")

@clawnode(id="global_coord", bag="reg_ops", skills=["reg_ops/global_coordination.md"], tools=["gmail_api"])
def coordinate_global(inputs: dict) -> ClawOutput:
    return ClawOutput(signal=Signal.DONE, summary="Global filing ready.")

# --- BAG 5: Strategy_Labeling_Bag ---

@clawnode(id="risk_assess", bag="strategy_labeling", skills=["strategy/risk_negotiation.md"], tools=["google_search"])
def assess_risk(inputs: dict) -> ClawOutput:
    return ClawOutput(signal=Signal.DONE, summary="Market risk assessed.")

@clawnode(id="label_negotiator", bag="strategy_labeling", skills=["strategy/approval_strategy.md"], tools=["pdf_parser"])
def negotiate_label(inputs: dict) -> ClawOutput:
    return ClawOutput(signal=Signal.DONE, summary="USPI optimization draft ready.")

@clawnode(id="ccds_manager", bag="strategy_labeling", skills=["labeling/leaflets_ccds.md"], tools=["pdf_parser"])
def manage_ccds(inputs: dict) -> ClawOutput:
    return ClawOutput(signal=Signal.DONE, summary="CCDS aligned with Safety Signals.")

# --- BAG 6: Marketing_Bag ---

@clawnode(id="press_writer", bag="marketing", skills=["marketing/press_release.md"], tools=["gmail_api"])
def write_pr(inputs: dict) -> ClawOutput:
    return ClawOutput(signal=Signal.DONE, summary="Press Release drafted.")
