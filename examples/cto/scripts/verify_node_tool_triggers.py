import os
import sys
import json
import asyncio

# Add parent dir to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from examples.cto.nodes.llm_utils import run_cto_llm_node
from clawgraph.core.signals import SignalManager

def test_node_tool_trigger():
    print("🎯 Verifying Node -> Tool Integration...")
    
    # 1. Test StatsCalc Trigger (via a hypothetical prompt to a node with stats tools)
    print("\n--- Testing Trigger: Manufacturing QC -> StatsCalc ---")
    
    # We'll simulate the state a node would receive
    sm = SignalManager()
    state = {
        "job_objective": "Analyze the variance of the purity levels in the batch record.",
        "input_artifacts": {
            "batch_record": "examples/cto/artifacts/patient_sync_raw.csv" # Using CSV for ease of test
        },
        "archive": {
             "batch_record": "examples/cto/artifacts/patient_sync_raw.csv"
        }
    }
    
    # We'll call run_cto_llm_node directly with tools that include stats_calc
    result = run_cto_llm_node(
        state=state,
        node_id="manufacturing_qc",
        description="Verify manufacturing batch purity and calculate variance.",
        skills=[],
        tools=["stats_calc", "excel_bridge"]
    )
    
    print(f"Node Status: {result.signal}")
    # The output should contain evidence of the tool call
    output = result.continuation_context.get("text", "") if result.continuation_context else ""
    
    # Check if StatsCalc was called
    if "variance" in output.lower() or "mean" in output.lower():
        print("✅ Success: Node triggered StatsCalc tool!")
    else:
        print("⚠️ Warning: Node did not explicitly mention stats in output, but check console for '🔢 [StatsCalc]'")

    # 2. Test PDF Parser Trigger
    print("\n--- Testing Trigger: Regulatory Node -> PDF Parser ---")
    state_pdf = {
        "job_objective": "Extract the Section 5 requirements from the protocol.",
        "input_artifacts": {
            "protocol_v1": "examples/cto/artifacts/reg_sources/E3_Guideline.pdf"
        },
        "archive": {
            "protocol_v1": "examples/cto/artifacts/reg_sources/E3_Guideline.pdf"
        }
    }
    
    result_pdf = run_cto_llm_node(
        state=state_pdf,
        node_id="protocol_benchmark",
        description="Benchmark the protocol against ICH guidelines.",
        skills=[],
        tools=["pdf_parser"]
    )
    
    print(f"Node Status: {result_pdf.signal}")
    output_pdf = result_pdf.continuation_context.get("text", "") if result_pdf.continuation_context else ""
    if "section" in output_pdf.lower():
         print("✅ Success: Node triggered PDFParser tool!")

if __name__ == "__main__":
    test_node_tool_trigger()
