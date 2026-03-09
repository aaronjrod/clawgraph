import contextlib
import json
import os
import threading
import time
from datetime import UTC, datetime
from typing import Any

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel
from pydantic.json import pydantic_encoder

app = FastAPI()

# Add CORS middleware to allow all origins for development purposes
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods
    allow_headers=["*"],  # Allows all headers
)

# Global list of bags to track
_TRACKED_BAGS: list[Any] = []
# Global list to store chat messages
_CHAT_LOGS: list[dict[str, Any]] = []

# Pydantic model for chat messages
class ChatMessage(BaseModel):
    sender: str
    text: str
    timestamp: str | None = None

def set_tracked_bags(bags: list[Any]) -> None:
    global _TRACKED_BAGS
    _TRACKED_BAGS = bags

@app.get("/")
def get_index() -> HTMLResponse:
    # Use the premium dashboard file
    path = os.path.join(os.path.dirname(__file__), "timeline_hud.html")
    with open(path) as f:
        html = f.read()
    return HTMLResponse(content=html)

@app.get("/api/snapshot")
def get_snapshot() -> JSONResponse:
    global _TRACKED_BAGS
    global _CHAT_LOGS
    snapshot_data = {
        "bags": [],
        "documents": {}
    }

    for bag in _TRACKED_BAGS:
        # Get the standard HUD snapshot for this bag
        # This now includes nodes and links natively from SignalManager
        bag_snap = bag.get_hud_snapshot()

        # Collect any documents associated with this bag from its signal manager
        for node_id, uri in bag.signal_manager._result_uris.items():
            if uri not in snapshot_data["documents"]:
                snapshot_data["documents"][uri] = {
                    "uri": uri,
                    "domain": bag.name,
                    "owner_node": node_id,
                    "version": "v1.0",
                    "last_modified": datetime.now(UTC).isoformat()
                }

        # Extract timeline events for the active thread
        thread_id = bag.signal_manager._active_thread_id
        raw_events = []
        if thread_id and bag.signal_manager._timeline:
            events = bag.signal_manager._timeline.get_timeline(thread_id)
            for e in events:
                raw_events.append({
                    "event_id": e.event_id,
                    "node_id": e.node_id,
                    "signal": e.signal.value if e.signal else None,
                    "summary": e.summary,
                    "metadata": e.metadata,
                    "timestamp": e.timestamp.isoformat() if e.timestamp else datetime.now(UTC).isoformat()
                })

        snapshot_data["bags"].append({
            "name": bag.name,
            "status": bag.signal_manager.overall_status,
            "nodes": bag_snap["nodes"],
            "links": bag_snap["links"],
            "timeline": raw_events
        })

    # Merge global chat logs and bag timeline events into one chronologically sorted chat log
    unified_chat = list(_CHAT_LOGS)

    for bag_data in snapshot_data["bags"]:
        for event in bag_data["timeline"]:
            # Synthesize an event dict that looks like a chat message for sorting
            unified_chat.append({
                "sender": "ORCHESTRATOR",
                "text": f"[{bag_data['name'].upper()}] {event['summary']}",
                "timestamp": event.get("timestamp", datetime.now(UTC).isoformat()),
                "signal": event.get("signal"),
                "node_id": event.get("node_id"),
                "metadata": event.get("metadata", {})
            })

    # Sort unified chat by timestamp if available
    with contextlib.suppress(Exception):
        unified_chat.sort(key=lambda x: x.get("timestamp", ""))

    snapshot_data["chat_log"] = unified_chat

    # Custom serialization to handle Enums/Models cleanly
    encoded = json.dumps(snapshot_data, default=pydantic_encoder)
    return JSONResponse(content=json.loads(encoded))

@app.post("/api/chat")
def post_chat(msg: ChatMessage):
    """Allows Human or Super-Orchestrator to inject messages into the timeline HUD."""
    timestamp = msg.timestamp or datetime.now(UTC).isoformat()
    # Accept standard message
    log_entry = {
        "sender": msg.sender.upper(),
        "text": msg.text,
        "timestamp": timestamp
    }
    # Extract destination bag if specified (e.g. [TO: CLINICAL_OPS] message)
    text = msg.text
    target_bag_name = None
    if text.startswith("[TO: "):
        try:
            end_idx = text.index("]")
            target_bag_name_raw = text[5:end_idx].strip()

            # Allow case-insensitive matching and handle spaces/underscores
            for bag in _TRACKED_BAGS:
                if bag.name.upper() == target_bag_name_raw.upper() or bag.name.replace("_", " ").upper() == target_bag_name_raw.upper():
                    target_bag_name = bag.name
                    break

            text = text[end_idx+1:].strip()

            if target_bag_name:
                log_entry["text"] = f"[TO: {target_bag_name.upper()}] {text}"

        except ValueError:
             pass

    _CHAT_LOGS.append(log_entry)

    # If the sender is human/architect, we log it to console as well
    print(f"\n[{log_entry['sender']}] {log_entry['text']}\n")

    # Record in the target bag's signal manager if possible
    if target_bag_name:
        for bag in _TRACKED_BAGS:
            if bag.name == target_bag_name:
                bag.signal_manager.record_chat(msg.sender, text)
                break
    else:
        # If no specific bag, record in all active bags
        for bag in _TRACKED_BAGS:
            bag.signal_manager.record_chat(msg.sender, text)

    # Actually resume the simulation if it's waiting for human input
    if msg.sender.upper() in ["HUMAN", "ARCHITECT"]:
        for bag in _TRACKED_BAGS:
            if target_bag_name and bag.name != target_bag_name:
                continue

            if bag.signal_manager.overall_status == "SUSPENDED":
                thread_id = bag.signal_manager._active_thread_id
                if thread_id:
                    print(f"[SERVER] Resuming thread {thread_id} in {bag.name} with user input...")

                    # Store the human response in the bag's signal manager so the LLM context has it
                    if not hasattr(bag.signal_manager, "_human_responses"):
                        bag.signal_manager._human_responses = {}
                    bag.signal_manager._human_responses[thread_id] = text

                    # Fire and forget the resume task in a separate thread so we don't block the API response
                    def resume_task():
                        bag.resume_job(thread_id, user_approval=True)
                    threading.Thread(target=resume_task).start()

                    # If we found a specific target bag and resumed it, we can stop searching
                    if target_bag_name:
                        break

    return {"status": "ok"}

@app.get("/api/documents/{doc_uri:path}")
def get_document(doc_uri: str):
    """Retrieves the raw content of a document by its URI for HUD previews."""
    content = f"# Artifact: {doc_uri}\n\nContent is being generated by the orchestrator. Please refresh shortly."

    # Check if it's a local file mapped in our artifacts folder
    if doc_uri.startswith("file://"):
        filepath = doc_uri.replace("file://", "")
        if filepath.startswith("/seed/"):
            return {"uri": doc_uri, "content": f"# Seed Document: {filepath}\nThis is an initial seed document to satisfy prerequisites."}

        if os.path.exists(filepath):
            with open(filepath) as f:
                content = f.read()
                return {"uri": doc_uri, "content": content}

    # If the document is not a mapped local file, we return a synthesized stub
    return {"uri": doc_uri, "content": content}

def run_server(port: int = 8000) -> None:
    uvicorn.run(app, host="127.0.0.1", port=port, log_level="error")

def start_background_server(port: int = 8000) -> threading.Thread:
    thread = threading.Thread(target=run_server, args=(port,), daemon=True)
    thread.start()
    time.sleep(1)
    return thread
