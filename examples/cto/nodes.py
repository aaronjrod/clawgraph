"""
ClawGraph Expert Example: Clinical Trial Operations (CTO)
Architecture: One Bag Per Specialist | One Node Per Task
"""

from clawgraph import clawnode, ClawOutput, Signal

# --- BAG: Regulatory_Bag (Specialist: Regulatory Affairs) ---

@clawnode(
    id="benchmark_task",
    bag="regulatory_specialist",
    skills=["regulatory/protocol_benchmarking.md"],
    model="claude-3-5-sonnet"
)
def protocol_benchmark(inputs: dict) -> ClawOutput:
    # Logic: Benchmarking Disease A vs B
    return ClawOutput(signal=Signal.DONE, summary="Benchmark complete.")

@clawnode(
    id="ib_justification_task",
    bag="regulatory_specialist",
    skills=["regulatory/ib_justification.md"],
    model="claude-3-5-sonnet"
)
def write_ib_justification(inputs: dict) -> ClawOutput:
    # Logic: Cross-disease justification
    return ClawOutput(signal=Signal.DONE, summary="IB justified.")

# --- BAG: CMC_Bag (Specialist: Chemistry, Mfg & Controls) ---

@clawnode(
    id="coa_parse_task",
    bag="cmc_specialist",
    skills=["cmc/coa_parsing.md"],
    model="gemini-1.5-flash"
)
def parse_coa(inputs: dict) -> ClawOutput:
    # Logic: 30 parameters + missing param detection
    return ClawOutput(signal=Signal.DONE, summary="CoA Parsed.")

@clawnode(
    id="aggregation_task",
    bag="cmc_specialist",
    skills=["cmc/facility_aggregation.md"],
    model="claude-3-5-sonnet"
)
def aggregate_facilities(inputs: dict) -> ClawOutput:
    # Logic: multi-facility variance alignment
    return ClawOutput(signal=Signal.DONE, summary="Data aggregated.")

# --- BAG: Patient_Ops_Bag (Specialist: Clinical Trial Ops) ---

@clawnode(
    id="doc_integrity_task",
    bag="patient_ops",
    skills=["patient_ops/document_checker.md"],
    model="claude-3-5-sonnet"
)
def check_document_alignment(inputs: dict) -> ClawOutput:
    # Logic: Catching NM5072 vs NM5082 mismatches
    return ClawOutput(
        signal=Signal.NEED_INTERVENTION, 
        summary="NM5072 found in NM5082 dossier. Escalating to SO."
    )

@clawnode(
    id="sheet_sync_task",
    bag="patient_ops",
    skills=["patient_ops/daily_sheet_sync.md"],
    model="gemini-1.5-flash"
)
def sync_daily_sheets(inputs: dict) -> ClawOutput:
    # Logic: Global timezone Excel sync
    return ClawOutput(signal=Signal.DONE, summary="Excel sync complete.")
