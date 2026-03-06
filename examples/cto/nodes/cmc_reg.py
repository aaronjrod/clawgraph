from clawgraph import ClawOutput, Signal, clawnode
from clawgraph.bag.patterns import VerificationNode, CheckResult

@clawnode(
    id="manage_stability",
    description="Monitors product stability data and flags deviations in impurity profiles.",
    bag="cmc_regulatory",
    requires=["stability_test_report_q1"],
    skills=["cmc_reg/stability_analysis.md"]
)
def manage_stability(state: dict) -> ClawOutput:
    vn = VerificationNode("manage_stability")
    checks = [
        CheckResult(name="Impurity A limit check", passed=True, expected="< 0.05%", actual="0.045%"),
        CheckResult(name="Impurity B limit check", passed=False, expected="< 0.10% (safe margin)", actual="0.098%", message="Drifting near upper control limit.")
    ]
    
    import os
    abs_path = os.path.abspath("examples/cto/artifacts/generated/stability-assessment-q1.md")
    return vn.evaluate(
        checks=checks,
        artifact_uri=f"file://{abs_path}"
    )

@clawnode(
    id="mod3_author",
    description="Authors Module 3 technical documentation.",
    bag="cmc_regulatory",
    skills=["cmc_reg/module_3_authoring.md"],
    tools=["pdf_parser"],
)
def author_mod3(state: dict) -> ClawOutput:
    import os
    abs_path = os.path.abspath("examples/cto/artifacts/generated/module3.md")
    return ClawOutput(
        signal=Signal.DONE,
        node_id="mod3_author",
        orchestrator_summary="Module 3 updated.",
        result_uri=f"file://{abs_path}",
    )

@clawnode(
    id="process_val",
    description="Validates drug substance manufacturing processes.",
    bag="cmc_regulatory",
    skills=["cmc_reg/drug_substance_process_validation.md"],
    tools=["stats_calc"],
)
def validate_process(state: dict) -> ClawOutput:
    import os
    abs_path = os.path.abspath("examples/cto/artifacts/generated/process_validation.md")
    return ClawOutput(
        signal=Signal.DONE,
        node_id="process_val",
        orchestrator_summary="Manufacturing comparability confirmed.",
        result_uri=f"file://{abs_path}",
    )

@clawnode(
    id="manufacturing_qc",
    description="Validates manufacturing batch records against chemical controls.",
    bag="cmc_regulatory",
    requires=["batch_record"],
)
def qc_batch(state: dict) -> ClawOutput:
    archive = state.get("document_archive", {})
    if "batch_record" not in archive:
        return ClawOutput(signal=Signal.STALLED, node_id="manufacturing_qc", orchestrator_summary="Awaiting batch record.")
    import os
    abs_path = os.path.abspath("examples/cto/artifacts/generated/manufacturing_batch_record_v1.md")
    return ClawOutput(
        signal=Signal.DONE,
        node_id="manufacturing_qc",
        orchestrator_summary="Passed QC on Lot BR-9002. Active ingredient formulation deviates by 0.1% from target, but remains dynamically within acceptable stability margins.",
        result_uri=f"file://{abs_path}"
    )
