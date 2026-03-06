import inspect
import logging
import os
import sys

import requests

# Add parent dir to path so clawgraph modules load
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

import nodes
import server

logging.basicConfig(level=logging.ERROR)

def post_chat(text: str):
    requests.post("http://localhost:8000/api/chat", json={"sender": "SUPER-ORCHESTRATOR", "text": text})

bags = [
    nodes.clinical_reg_bag,
    nodes.cmc_reg_bag,
    nodes.clinical_ops_bag,
    nodes.reg_ops_bag,
    nodes.strategy_labeling_bag,
    nodes.marketing_bag,
]

for _name, obj in inspect.getmembers(nodes):
    if inspect.isfunction(obj) and hasattr(obj, "_clawnode_metadata"):
        meta = obj._clawnode_metadata
        for bag in bags:
            if bag.name == meta.bag:
                bag.manager.register_node(obj)
                break

server.set_tracked_bags(bags)
server.start_background_server(port=8000)

# --- Auto-Start Simulation for Demo Purposes ---
print("\n[INFO] Auto-triggering multi-domain simulation jobs...")

# Set up initial input documents for the newly wired nodes
reg_ops_inputs = {
    "source_docs": "uri://artifacts/source_docs_v1.md",
    "unformatted_modules": "uri://artifacts/unformatted_modules_v2.md",
    "regional_clearance": "uri://artifacts/regional_clearance_q3.md"
}

strategy_inputs = {
    "clinical_data": "uri://artifacts/clinical_data_interim.md",
    "preliminary_label": "uri://artifacts/preliminary_label_v1.md",
    "safety_signals": "uri://artifacts/safety_signals_q2.md"
}

marketing_inputs = {
    "milestone_confirmation": "uri://artifacts/milestone_confirmation_memo.md"
}

# Start all bag workflows concurrently
nodes.clinical_reg_bag.start_job("Run core regulatory trial design")
nodes.cmc_reg_bag.start_job("Run quality checks on synthesis lot")
nodes.clinical_ops_bag.start_job("Execute global site feasibility")
nodes.reg_ops_bag.start_job("Compile regulatory submission elements", inputs=reg_ops_inputs)
nodes.strategy_labeling_bag.start_job("Negotiate preliminary USPI labels", inputs=strategy_inputs)
nodes.marketing_bag.start_job("Draft press releases and communications", inputs=marketing_inputs)

print("\n=== SYSTEM ONLINE ===")
print("Server running on http://localhost:8000")
print("You are in a live interactive Python REPL.")
print("The simulation has been auto-started across 6 domains.")
print("Use `post_chat('message')` to broadcast to the HUD.")
print("="*21 + "\n")

