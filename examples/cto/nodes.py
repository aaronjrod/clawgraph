\"\"\"
ClawGraph Expert Example: Clinical Trial Operations (CTO)
Architecture: One Bag Per Specialist | One Node Per Task | Explicit Tool Authorization
\"\"\"

from clawgraph import clawnode, ClawOutput, Signal

# --- BAG: Regulatory_Bag (Specialist: Regulatory Affairs) ---

@clawnode(
    id="benchmark_task",
    bag="regulatory_specialist",
    skills=["regulatory/protocol_benchmarking.md"],
    tools=["google_search", "pdf_parser", "stats_calc"], # Authorized tools
    model="claude-3-5-sonnet"
)
def protocol_benchmark(inputs: dict) -> ClawOutput:
    # Logic: Benchmarking competitive protocols vs internal historicals
    return ClawOutput(signal=Signal.DONE, summary="Benchmark complete.")

@clawnode(
    id="ib_justification_task",
    bag="regulatory_specialist",
    skills=["regulatory/ib_justification.md"],
    tools=["pdf_parser", "stats_calc"],
    model="claude-3-5-sonnet"
)
def write_ib_justification(inputs: dict) -> ClawOutput:
    # Logic: Scientific bridge between NM5072 and NM5082
    return ClawOutput(signal=Signal.DONE, summary="IB justified.")

# --- BAG: CMC_Bag (Specialist: Chemistry, Mfg & Controls) ---

@clawnode(
    id="coa_parse_task",
    bag="cmc_specialist",
    skills=["cmc/coa_parsing.md"],
    tools=["pdf_parser", "excel_bridge"],
    model="gemini-1.5-flash"
)
def parse_coa(inputs: dict) -> ClawOutput:
    # Logic: 30-param parsing with missing metadata detection
    return ClawOutput(signal=Signal.DONE, summary="CoA Parsed.")

@clawnode(
    id="aggregation_task",
    bag="cmc_specialist",
    skills=["cmc/facility_aggregation.md"],
    tools=["stats_calc", "pdf_parser"],
    model="claude-3-5-sonnet"
)
def aggregate_facilities(inputs: dict) -> ClawOutput:
    # Logic: Variance fence (2%) enforcement
    return ClawOutput(signal=Signal.DONE, summary="Data aggregated.")

# --- BAG: Patient_Ops_Bag (Specialist: Clinical Trial Ops) ---

@clawnode(
    id="doc_integrity_task",
    bag="patient_ops",
    skills=["patient_ops/document_checker.md"],
    tools=["pdf_parser", "stats_calc", "notary_log"],
    model="claude-3-5-sonnet"
)
def check_document_alignment(inputs: dict) -> ClawOutput:
    # Logic: Catching NM5072 vs NM5082 mismatches!
    # If typo found:
    return ClawOutput(
        signal=Signal.NEED_INTERVENTION, 
        summary="NM5072 found in NM5082 dossier. Possible copy-paste error.",
        error_detail={"severity": "CRITICAL", "node_to_fix": "benchmark_task"}
    )

@clawnode(
    id="abnormal_triage_task",
    bag="patient_ops",
    skills=["patient_ops/abnormality_triage.md"],
    tools=["google_search", "pdf_parser", "gmail_api"],
    model="claude-3-5-sonnet"
)
def triage_site_abnormalities(inputs: dict) -> ClawOutput:
    # Logic: Liver enzyme elevation mechanism research
    return ClawOutput(
        signal=Signal.HOLD_FOR_HUMAN,
        summary="Mechanism for ALT elevation drafted. Pending Physician sign-off.",
        result_uri="s3://trials/NM5082/reports/site01_triage.pdf"
    )

@clawnode(
    id="sheet_sync_task",
    bag="patient_ops",
    skills=["patient_ops/daily_sheet_sync.md"],
    tools=["excel_bridge", "gmail_api"],
    model="gemini-1.5-flash"
)
def sync_daily_sheets(inputs: dict) -> ClawOutput:
    # Logic: 24h timezone heartbeat check
    return ClawOutput(signal=Signal.DONE, summary="Heartbeat sync complete.")
