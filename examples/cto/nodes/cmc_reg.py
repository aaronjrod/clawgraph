from typing import Any

from clawgraph import ClawOutput, Signal, clawnode

from .llm_utils import run_cto_llm_node


@clawnode(
    id="manage_stability",
    description="Monitors product stability data and flags deviations in impurity profiles.",
    bag="cmc_regulatory",
    requires=["stability_test_report_q1"],
    skills=["cmc_reg/stability_analysis.md"],
)
def manage_stability(state: dict[str, Any]) -> ClawOutput:
    return run_cto_llm_node(
        node_id="manage_stability",
        description="Monitors product stability data and flags deviations in impurity profiles.",
        state=state,
        skills=["cmc_reg/stability_analysis.md"],
    )


@clawnode(
    id="mod3_author",
    description="Synthesize the CMC Quality Summary and Module 3 technical documentation based on Drug Substance stability data (ICH M4Q sections).",
    bag="cmc_regulatory",
    skills=["cmc_reg/module_3_authoring.md", "cmc/ich_m4q_r2_quality.md"],
    tools=["pdf_parser"],
)
def author_mod3(state: dict[str, Any]) -> ClawOutput:
    return run_cto_llm_node(
        node_id="mod3_author",
        description="Synthesize the CMC Quality Summary and Module 3 technical documentation based on Drug Substance stability data (ICH M4Q sections).",
        state=state,
        skills=["cmc_reg/module_3_authoring.md", "cmc/ich_m4q_r2_quality.md"],
        tools=["pdf_parser"],
    )


@clawnode(
    id="process_val",
    description="Validates drug substance manufacturing processes.",
    bag="cmc_regulatory",
    skills=["cmc_reg/drug_substance_process_validation.md"],
    tools=["stats_calc"],
)
def validate_process(state: dict[str, Any]) -> ClawOutput:
    return run_cto_llm_node(
        node_id="process_val",
        description="Validates drug substance manufacturing processes.",
        state=state,
        skills=["cmc_reg/drug_substance_process_validation.md"],
        tools=["stats_calc"],
    )


@clawnode(
    id="manufacturing_qc",
    description="Validates manufacturing batch records against chemical controls.",
    bag="cmc_regulatory",
    requires=["batch_record"],
)
def qc_batch(state: dict[str, Any]) -> ClawOutput:
    archive = state.get("document_archive", {})
    if "batch_record" not in archive:
        return ClawOutput(
            signal=Signal.HOLD_FOR_HUMAN,
            node_id="manufacturing_qc",
            orchestrator_summary="Awaiting batch record.",
        )
    return run_cto_llm_node(
        node_id="manufacturing_qc",
        description="Validates manufacturing batch records against chemical controls.",
        state=state,
        skills=[],
        tools=["excel_bridge", "pdf_parser"],
    )
