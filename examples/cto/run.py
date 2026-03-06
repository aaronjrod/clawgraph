import inspect
import logging
import os
import sys

# Add parent dir to path so clawgraph modules load
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))


# Import nodes to register them within the bags
import nodes

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

    print("\n--- Cross-Domain Objective ---")
    objective = "Execute standard NDA submission package preparation."
    print(f"Goal: {objective}\n")

    # We'll just run one of the bags for a quick orchestrator demonstration.
    # In a full app, a Super-Orchestrator would spawn jobs across multiple bags.
    demo_bag = nodes.clinical_reg_bag

    print(f"\n[ORCHESTRATOR] Starting Job on {demo_bag.name}...")
    state = demo_bag.start_job(objective=objective)

    print("\n========================================")
    print(" JOB COMPLETE")
    print("========================================")
    print(f"Final State Status: {'SUSPENDED' if state.get('suspended') else 'FINISHED'}")

    print("\nPhase History:")
    for h in state.get("phase_history", []):
        print(f"  {h}")

    print("\nFinal Output (from last node):")
    output = state.get("current_output", {})
    if output and output.get("continuation_context"):
        print(output["continuation_context"].get("text", "N/A"))
    else:
        print("N/A")


if __name__ == "__main__":
    main()
