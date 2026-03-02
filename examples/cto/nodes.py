\"\"\"
ClawGraph Expert Example: Clinical Trial Operations (CTO)
Demonstrating the @clawnode(bag=...) pattern and complex signals.
\"\"\"

from clawgraph import clawnode, ClawOutput, Signal

# --- BAG: NM5082_Clinical_Trial ---

@clawnode(
    id="patient_coordinator",
    bag="NM5082_trial",
    skills=["patient_coordination.md"],
    model="gemini-1.5-flash" # Speed for daily sheet management
)
def manage_daily_updates(inputs: dict) -> ClawOutput:
    # Logic: Sync Excel sheets across timezones
    # If abnormality detected:
    return ClawOutput(
        signal=Signal.HOLD_FOR_HUMAN,
        summary="Patient Site-01 abnormality detected. Pending Physician check.",
        result_uri="s3://trials/NM5082/reports/site01_abnormality.pdf"
    )

@clawnode(
    id="document_alignment_checker",
    bag="NM5082_trial",
    skills=["document_alignment_checker.md"],
    model="claude-3-5-sonnet" # Complex reasoning for entity cross-check
)
def check_entity_consistency(inputs: dict) -> ClawOutput:
    # Logic: Scan all documents for "NM5072" vs "NM5082"
    # Found mistake:
    return ClawOutput(
        signal=Signal.NEED_INTERVENTION,
        summary="Drug name mismatch: Found 'NM5072' in CMC section. Should be 'NM5082'.",
        error_detail={"target_nodes": ["cmc_stability_checker"], "fix": "Correction of drug ID"},
        result_uri="s3://trials/NM5082/audit/mismatch_report.json"
    )

# --- BAG: Regulatory_Submissions ---

@clawnode(
    id="regulatory_specialist",
    bag="regulatory_submissions",
    skills=["regulatory_affairs.md"],
    model="claude-3-5-sonnet"
)
def benchmark_protocol(inputs: dict) -> ClawOutput:
    # Logic: Compare Disease A vs Disease B
    return ClawOutput(
        signal=Signal.DONE,
        summary="Protocol benchmark complete. Justification for Disease B added to IB."
    )
