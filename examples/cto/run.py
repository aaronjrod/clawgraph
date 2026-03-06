import inspect
import logging
import os
import sys

# Add parent dir to path so clawgraph modules load
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))


# Import nodes to register them within the bags
import nodes
import server
import time

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)


def main():
    print("========================================")
    print(" CLAWGRAPH CTO ADVANCED EXAMPLE (MOCKED)")
    print("========================================")

    # We have 6 specific bags initialized in nodes.py
    bags = [
        nodes.clinical_reg_bag,
        nodes.cmc_reg_bag,
        nodes.clinical_ops_bag,
        nodes.reg_ops_bag,
        nodes.strategy_labeling_bag,
        nodes.marketing_bag,
    ]

    # Dynamically register all decorated nodes to their respective bags
    for _name, obj in inspect.getmembers(nodes):
        if inspect.isfunction(obj) and hasattr(obj, "_clawnode_metadata"):
            meta = obj._clawnode_metadata
            for bag in bags:
                if bag.name == meta.bag:
                    bag.manager.register_node(obj)
                    break

    print("\n--- Initialized Bags ---")
    for bag in bags:
        print(f"Bag: {bag.name} ({len(bag.manager.manifest.nodes)} nodes)")

    # Start HUD Server
    server.set_tracked_bags(bags)
    server.start_background_server(port=8000)
    print("\n[HUD] Live Dashboard started at http://localhost:8000")
    print("[HUD] Open this URL in your browser to see the real-time simulation.\n")

    print("--- Cross-Domain Objective ---")
    objective = "Execute standard NDA submission package preparation."
    print(f"Goal: {objective}\n")

    # Simulation Script: Iterate through key bags to show activity on the HUD
    active_sequence = [
        (nodes.clinical_reg_bag, "Drafting initial protocols and IND shell."),
        (nodes.cmc_reg_bag, "Analyzing batch stability and impurity drift."),
        (nodes.clinical_ops_bag, "Syncing patient data and tracking adverse events."),
        (nodes.reg_ops_bag, "Assembling eCTD submission sections.")
    ]

    for bag, desc in active_sequence:
        print(f"\n[ORCHESTRATOR] Activating Bag: {bag.name}")
        print(f"[ORCHESTRATOR] {desc}")
        
        # We simulate the job running by calling start_job
        # We add some sleeps so the user can see the cards change status in the HUD
        time.sleep(2)
        bag.start_job(objective=desc)
        time.sleep(3)

    print("\n========================================")
    print(" SIMULATION COMPLETE")
    print("========================================")
    print("The Dashboard is still live at http://localhost:8000")
    print("Press Ctrl+C to terminate the server.\n")

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nShutting down Command Center.")


if __name__ == "__main__":
    main()
