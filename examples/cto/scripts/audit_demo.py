import requests
import json
import time
import sys
import os

API_BASE = "http://localhost:8000/api"

def audit():
    try:
        response = requests.get(f"{API_BASE}/snapshot")
        if response.status_code != 200:
            print(f"Error: Server returned {response.status_code}")
            return

        snapshot = response.json()
        
        print("\n=== CTO SYSTEM AUDIT ===")
        print(f"Timestamp: {snapshot['bags'][0]['timeline'][-1]['timestamp'] if snapshot['bags'] and snapshot['bags'][0]['timeline'] else 'N/A'}")
        
        print("\nDomains Status:")
        for bag in snapshot["bags"]:
            status = bag["status"]
            node_counts = {
                "DONE": len([n for n in bag["nodes"] if n["status"] == "DONE"]),
                "WORKING": len([n for n in bag["nodes"] if n["status"] == "WORKING"]),
                "FAILED": len([n for n in bag["nodes"] if n["status"] == "FAILED"]),
                "HOLD": len([n for n in bag["nodes"] if n["status"] == "HOLD"]),
            }
            print(f"  [{bag['name'].upper()}] - Status: {status}")
            print(f"    Nodes: DONE={node_counts['DONE']}, WORKING={node_counts['WORKING']}, FAILED={node_counts['FAILED']}, HOLD={node_counts['HOLD']}")

        print("\nLatest Chat/Events:")
        for chat in snapshot["chat_log"][-5:]:
            print(f"  [{chat['sender']}] {chat['text']}")

        print("\nGenerated Documents:")
        for uri, info in snapshot["documents"].items():
            print(f"  - {info['owner_node']} -> {uri}")

    except Exception as e:
        print(f"Audit failed: {e}")

if __name__ == "__main__":
    continuous = "--continuous" in sys.argv
    while True:
        audit()
        if not continuous:
            break
        time.sleep(5)
