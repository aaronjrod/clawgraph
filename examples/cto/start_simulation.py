import inspect
import logging
import os
import sys
import time
from datetime import datetime

# Add parent dir to path so clawgraph modules load
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from dotenv import load_dotenv
load_dotenv()

import nodes
import server

LOG_DIR = os.path.join(os.path.dirname(__file__), "logs")
os.makedirs(LOG_DIR, exist_ok=True)
TIMESTAMP = datetime.now().strftime("%Y%m%d_%H%M%S")
LOG_FILE = os.path.join(LOG_DIR, f"cto_simulation_{TIMESTAMP}.log")

# Configure logging
root_logger = logging.getLogger()
root_logger.setLevel(logging.INFO)

# Use delay=False to ensure the file is opened and ready immediately
file_handler = logging.FileHandler(LOG_FILE, mode="w", delay=False)
stream_handler = logging.StreamHandler(sys.stdout)
formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")

for h in [file_handler, stream_handler]:
    h.setFormatter(formatter)
    root_logger.addHandler(h)

# Specifically ensure clawgraph loggers are at INFO and propagate to root
cg_logger = logging.getLogger("clawgraph")
cg_logger.setLevel(logging.INFO)
cg_logger.propagate = True

# Silence noisy external libraries
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("google.generativeai").setLevel(logging.WARNING)
logging.getLogger("google.ai").setLevel(logging.WARNING)

logger = logging.getLogger("clawgraph.cto")



def seed_initial_data(bags):
    """Seed the document archive with initial artifacts so nodes don't stall immediately."""
    print("\n--- Seeding Initial Artifacts ---")
    seeds = {
        "source_docs": "file:///seed/source_docs.pdf",
        "protocol_v1": "file:///seed/protocol_v1.pdf",
        "batch_record": "file:///seed/batch_record_alpha9.pdf",
        "patient_data": "file:///seed/patient_sync_raw.csv",
        "submission_plan": "file:///seed/submission_plan_2026.pdf",
        "unformatted_modules": "file:///seed/module_drafts.zip",
        "regional_clearance": "file:///seed/regional_dispatch.json",
    }
    for bag in bags:
        for k, v in seeds.items():
            bag.signal_manager.record_input_artifact(k, v)
    return seeds

def main():
    print("========================================")
    print(" CLAWGRAPH CTO - REACTIVE CONTROL HUB")
    print("========================================")

    # Resolve bags
    bags = nodes.all_bags

    # Dynamically register all decorated nodes
    print("\n--- Registering Nodes ---")
    for _name, obj in inspect.getmembers(nodes):
        if inspect.isfunction(obj) and hasattr(obj, "_clawnode_metadata"):
            meta = obj._clawnode_metadata
            for bag in bags:
                if bag.name == meta.bag:
                    bag.manager.register_node(obj, warn_discovery=False)
                    print(f"Registered {obj.__name__} in {bag.name}")
                    break

    # Seed initial artifacts
    seed_initial_data(bags)

    # Start HUD Server
    server.set_tracked_bags(bags)
    server.start_background_server(port=8000)
    
    print("\n[HUD] Live Dashboard started at http://localhost:8000")
    print("[LOGS] reasoning being written to: " + LOG_FILE)
    print("\n[CONTROL] Waiting for Super-Orchestrator instructions via API...")
    print("Example: curl -X POST http://localhost:8000/api/chat -H 'Content-Type: application/json' -d '{\"sender\": \"HUMAN\", \"text\": \"[TO: CLINICAL_REGULATORY] Execute standard NDA submission package preparation.\"}'")

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nShutting down Control Hub.")

if __name__ == "__main__":
    main()

