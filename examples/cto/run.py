import inspect
import logging
import os
import sys
import threading
from datetime import datetime

# Add parent dir to path so clawgraph modules load
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from dotenv import load_dotenv
load_dotenv()

# Import nodes to register them within the bags
import nodes
import server
from server import ChatMessage

LOG_DIR = os.path.join(os.path.dirname(__file__), "logs")
os.makedirs(LOG_DIR, exist_ok=True)
TIMESTAMP = datetime.now().strftime("%Y%m%d_%H%M%S")
LOG_FILE = os.path.join(LOG_DIR, f"cto_simulation_{TIMESTAMP}.log")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(LOG_FILE, mode='w')
    ]
)
logger = logging.getLogger("clawgraph.cto")
print(f"[LOGS] Simulation logs being written to: {LOG_FILE}")

def seed_initial_data(bags):
    """Seed the document archive with initial artifacts so nodes don't stall immediately."""
    print("\n--- Seeding Initial Artifacts ---")
    
    # Generic seeds
    seeds = {
        "source_docs": "file:///seed/source_docs.pdf",
        "protocol_v1": "file:///seed/protocol_v1.pdf",
        "batch_record": "file:///seed/batch_record_alpha9.pdf",
        "patient_data": "file:///seed/patient_sync_raw.csv",
        "submission_plan": "file:///seed/submission_plan_2026.pdf",
        "unformatted_modules": "file:///seed/module_drafts.zip",
        "regional_clearance": "file:///seed/regional_dispatch.json"
    }
    
    return seeds

def main():
    print("========================================")
    print(" CLAWGRAPH CTO ADVANCED EXAMPLE")
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
    print("[HUD] Roleplay as the Human or Super-Orchestrator to move the simulation forward.\n")

    seed_data = seed_initial_data(bags)

    print("\n--- Cross-Domain Objective ---")
    objective = "Execute standard NDA submission package preparation."
    print(f"Goal: {objective}\n")

    # Simulation Script
    active_sequence = [
        (nodes.clinical_reg_bag, "Drafting initial protocols and IND shell."),
        (nodes.cmc_reg_bag, "Analyzing batch stability and impurity drift."),
        (nodes.clinical_ops_bag, "Syncing patient data and tracking adverse events."),
        (nodes.reg_ops_bag, "Assembling eCTD submission sections.")
    ]

    for bag, desc in active_sequence:
        print(f"\n[ORCHESTRATOR] Activating Bag: {bag.name}")
        server.post_chat(ChatMessage(sender="ORCHESTRATOR", text=f"Starting job in {bag.name}: {desc}"))

        # Inject seeds into the initial archive and signal manager for HUD visibility
        for k, v in seed_data.items():
            bag.signal_manager.record_input_artifact(k, v)
        
        # start_job accepts 'inputs' dict
        bag.start_job(objective=desc, inputs=seed_data)
        time.sleep(2)

    print("\n" + "="*40)
    print("         SIMULATION COMPLETE")
    print("========================================")
    print(f"HUD: http://localhost:8000")
    print("The system is now fully automated and interactive.\n")

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nShutting down Command Center.")


if __name__ == "__main__":
    main()
