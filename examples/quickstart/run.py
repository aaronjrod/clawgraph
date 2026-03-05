import logging
import os
import sys

from dotenv import load_dotenv

# Add parent dir to path so clawgraph modules load
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from clawgraph import ClawBag

from llm_node import build_llm_node
from server import start_background_server, set_active_bag

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")

load_dotenv()

def main():
    if not os.getenv("GEMINI_API_KEY"):
        print("\n[!] ERROR: GEMINI_API_KEY environment variable is required.")
        print("Please export it or add it to a .env file.\n")
        sys.exit(1)

    print("========================================")
    print(" CLAWGRAPH LIVE INTEGRATION DEMO")
    print("========================================")
    
    # 1. Initialize the Bag
    bag = ClawBag("live_demo_bag")
    
    # 2. Build our LLM-backed nodes using the builder
    build_llm_node(
        "researcher",
        "You are an expert researcher. Break down the objective into clear facts and find preliminary answers. You should always conclude with the DONE signal once you've provided the initial research.",
        bag
    )
    
    build_llm_node(
        "analyzer",
        "You are an expert data analyzer. Take the preliminary research and synthesize it into a strategic 3-point plan. Only output a DONE signal when your plan is solid.",
        bag
    )

    build_llm_node(
        "writer",
        "You an expert technical writer. Take the strategy and facts and write a beautifully formatted markdown report.",
        bag
    )
    
    # Hook the active bag to our live server singleton
    set_active_bag(bag)

    # 4. Start the background web server
    print("\n🚀 Starting Live HUD Server at http://127.0.0.1:8000")
    start_background_server(port=8000)
    print("--> Open http://127.0.0.1:8000 in your browser to watch the execution live!\n")
    
    import time
    print("Waiting 3 seconds for you to open the browser... 3")
    time.sleep(1)
    print("2")
    time.sleep(1)
    print("1")
    time.sleep(1)

    # 5. Kick off the orchestration job
    objective = "Research the architecture of LangGraph, analyze its strengths and weaknesses compared to completely autonomous agents, and write a short summary report of why a hybrid approach like ClawGraph is beneficial."
    
    print(f"\n[ORCHESTRATOR] Starting Job:\n   Objective: '{objective}'\n")
    
    state = bag.start_job(objective=objective)
    
    print("\n========================================")
    print(" JOB COMPLETE")
    print("========================================")
    print(f"Final State Status: {'SUSPENDED' if state.get('suspended') else 'FINISHED'}")
    print("\nPhase History:")
    for h in state.get('phase_history', []):
        print(f"  {h}")
        
    print("\nFinal Output (from last node):")
    output = state.get('current_output', {})
    if output and output.get('continuation_context'):
        print(output['continuation_context'].get('text', 'N/A'))
    else:
        print('N/A')
    
    # Keep server alive a bit more so user can see final payload on screen
    print("\n--> Keeping server alive for 30 seconds to view final HUD state. Press Ctrl+C to exit.")
    try:
        time.sleep(30)
    except KeyboardInterrupt:
        pass

if __name__ == "__main__":
    main()
