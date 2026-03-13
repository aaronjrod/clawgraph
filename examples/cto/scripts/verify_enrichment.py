import logging
import os
import sys
import inspect
from pprint import pprint

# Setup path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

import nodes
from clawgraph import Signal

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("verify_enrichment")

def run_node_verification(node_func, bag, inputs, expected_headers):
    print(f"\n[VERIFY] Testing Node: {node_func.__name__} in Bag: {bag.name}")
    print("-" * 50)
    
    # Register node
    bag.manager.register_node(node_func, warn_discovery=False)
    
    # Start job
    state = bag.start_job(
        objective=f"Verify high-fidelity output for {node_func.__name__}",
        inputs=inputs
    )
    
    # In ClawGraph, bag.start_job returns the final state dict.
    # The 'status' key in the bag state represents the overall job status.
    bag_status = state.get("status")
    print(f"Bag Status: {bag_status}")
    
    if bag_status == "DONE" or bag_status == "Signal.DONE":
        result_uri = state.get("current_output", {}).get("result_uri")
        if result_uri:
            path = result_uri.replace("file://", "")
            with open(path, "r") as f:
                content = f.read()
                print(f"Artifact Content Preview (first 200 chars):\n{content[:200]}...")
                
                missing = [h for h in expected_headers if h not in content]
                if not missing:
                    print(f"✅ SUCCESS: Found all expected headers: {expected_headers}")
                else:
                    print(f"❌ FAILURE: Missing headers: {missing}")
        else:
            print("❌ FAILURE: No result_uri found in output.")
    else:
        print(f"❌ FAILURE: Unexpected status: {status}")
        pprint(state.get("current_output"))

def main():
    # 1. Verify CMC Module 3 Authoring
    run_node_verification(
        nodes.author_mod3,
        nodes.cmc_reg_bag,
        {"stability_test_report_q1": "file:///seed/stability_test_report_q1.pdf"},
        ["Quality Overall Summary", "3.2.S", "3.2.P"]
    )
    
    # 2. Verify Clinical Ops SAE Narration
    run_node_verification(
        nodes.scribe_visit,
        nodes.clinical_ops_bag,
        {"patient_data": "file:///seed/patient_sync_raw.csv"},
        ["Serious Adverse Event", "Subject ID", "Causality Assessment"]
    )
    
    # 3. Verify Regulatory Admin Package
    run_node_verification(
        nodes.publish_submission,
        nodes.reg_ops_bag,
        {"submission_plan": "file:///seed/submission_plan_2026.pdf"},
        ["FDA Form 356h", "Establishment Information", "Field 28"]
    )

if __name__ == "__main__":
    main()
