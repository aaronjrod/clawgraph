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
        bag_snap = bag.get_hud_snapshot()
                # Collect any documents associated with this bag
        for _node_id, uri in bag.signal_manager._result_uris.items():
            if uri not in snapshot_data["documents"]:
                # Create synthesized versioning metadata natively
                snapshot_data["documents"][uri] = {
                    "uri": uri,
                    "domain": bag.name,
                    "owner_node": None,
                    "version": "v1.0",
                    "last_modified": datetime.now(UTC).isoformat()
                }
        # Extract precise status using library enums
        bag_status = bag.signal_manager.overall_status
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
            "status": bag_status,
            "nodes": bag_snap["nodes"],
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
    _CHAT_LOGS.append(log_entry)

    # If the sender is human/architect, we log it to console as well
    print(f"\n[{log_entry['sender']}] {log_entry['text']}\n")
    return {"status": "ok"}

@app.get("/api/documents/{doc_uri:path}")
def get_document(doc_uri: str):
    """Retrieves the raw content of a document by its URI for HUD previews."""
    content = f"# Mock Content for {doc_uri}\n\nThis is a synthesized preview of the artifact."

    # Check if it's a local file mapped in our artifacts folder
    if doc_uri.startswith("file://"):
        filepath = doc_uri.replace("file://", "")
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
