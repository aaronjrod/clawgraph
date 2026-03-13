import logging
import os
import sys
from pprint import pprint

# Setup path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

import inspect

import nodes

logging.basicConfig(level=logging.INFO)


def test_drift_execution():
    print("\n[TEST] Executing CMC Regulatory Bag - Stability Check")
    print("--------------------------------------------------")

    # Use the bag defined in nodes.py
    bag = nodes.cmc_reg_bag

    # REGISTER NODES (This was missing!)
    for _name, obj in inspect.getmembers(nodes):
        if inspect.isfunction(obj) and hasattr(obj, "_clawnode_metadata"):
            meta = obj._clawnode_metadata
            if meta.bag == bag.name:
                bag.manager.register_node(obj)

    print(f"Bag Name: {bag.name}")
    print("Goal: Validate Batch Alpha-9 artifacts.")

    # We provide the stability_test_report_q1 as an input to satisfy the 'requires'
    state = bag.start_job(
        objective="Analyze storage stability.",
        inputs={"stability_test_report_q1": "uri://artifacts/stability_test_report_q1.md"},
    )

    print("\n[RESULT] Final Signal:", state.get("status"))

    # Look at the specific node output
    output = state.get("current_output", {})
    pprint(output)


if __name__ == "__main__":
    test_drift_execution()
