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

@clawnode(
    id="ind_submission",
    bag="clinical_regulatory",
    skills=["clinical_reg/ind_submissions.md"],
    tools=["pdf_parser", "notary_log"],
    model="claude-3-5-sonnet"
)
def manage_ind_submission(inputs: dict) -> ClawOutput:
    return ClawOutput(signal=Signal.DONE, summary="IND Package Prepared.")

@clawnode(
    id="protocol_benchmark",
    bag="clinical_regulatory",
    skills=["clinical_reg/protocol_development.md"],
    tools=["google_search", "pdf_parser"],
    model="claude-3-5-sonnet"
)
def benchmark_protocol(inputs: dict) -> ClawOutput:
    return ClawOutput(signal=Signal.DONE, summary="Protocol benchmarked vs Disease A.")

# --- BAG 2: CMC_Regulatory_Bag ---

@clawnode(
    id="stability_manager",
    bag="cmc_regulatory",
    skills=["cmc_reg/stability_data_management.md"],
    tools=["excel_bridge", "stats_calc"],
    model="claude-3-5-sonnet"
)
def manage_stability_trends(inputs: dict) -> ClawOutput:
    # Logic: If stability fails, this triggers a NEED_INTERVENTION signal
    # which the Super-Orchestrator routes to Clinical Reg.
    return ClawOutput(signal=Signal.DONE, summary="Stability trends within 0.1% impurity.")

# --- BAG 3: Clinical_Ops_Bag (The "Daily Heartbeat") ---

@clawnode(
    id="patient_sync",
    bag="clinical_ops",
    skills=["clinical_ops/patient_tracking_sync.md"],
    tools=["excel_bridge", "gmail_api"],
    model="gemini-1.5-flash"
)
def sync_patient_data(inputs: dict) -> ClawOutput:
    return ClawOutput(signal=Signal.DONE, summary="Daily timezone sync complete.")

@clawnode(
    id="lab_vetting",
    bag="clinical_ops",
    skills=["clinical_ops/lab_invoice_vetting.md"],
    tools=["pdf_parser", "stats_calc"],
    model="claude-3-5-sonnet"
)
def vet_lab_invoices(inputs: dict) -> ClawOutput:
    return ClawOutput(signal=Signal.DONE, summary="Invoices aligned with SoA.")

@clawnode(
    id="doc_integrity",
    bag="clinical_ops",
    skills=["clinical_ops/document_alignment_checker.md"],
    tools=["pdf_parser", "notary_log"],
    model="claude-3-5-sonnet"
)
def check_dossier_integrity(inputs: dict) -> ClawOutput:
    # THE EXPERT TRAP: Found NM5072 in an NM5082 document
    return ClawOutput(
        signal=Signal.NEED_INTERVENTION,
        summary="NM5072 found in NM5082 protocol.",
        error_detail={"severity": "CRITICAL", "action": "REGENERATE_PROTOCOL"}
    )

# --- BAG 4: Reg_Ops_Bag ---
@clawnode(
    id="ectd_publisher",
    bag="reg_ops",
    skills=["reg_ops/ectd_publishing.md"],
    tools=["pdf_parser"],
    model="gemini-1.5-flash"
)
def publish_ectd(inputs: dict) -> ClawOutput:
    return ClawOutput(signal=Signal.DONE, summary="eCTD Package Validated.")

# --- BAG 5: Strategy_Bag & Labeling ---
# (Additional nodes for NDA Strategy, Risk Assessment, and USPI updates)
