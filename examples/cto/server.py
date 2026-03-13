import contextlib
import json
import os
import threading
import time
from datetime import UTC, datetime
from typing import Any

import logging
import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel
from pydantic.json import pydantic_encoder

app = FastAPI()
logger = logging.getLogger("clawgraph.server")

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
    snapshot_data = {"bags": [], "documents": {}}

    # 1. Scan global artifact directories for all files
    artifact_dirs = [
        os.path.abspath(os.path.join(os.path.dirname(__file__), "artifacts/generated")),
        os.path.abspath(os.path.join(os.path.dirname(__file__), "artifacts/reg_sources")),
    ]
    
    for adir in artifact_dirs:
        if os.path.exists(adir):
            for root, _, files in os.walk(adir):
                for f in files:
                    if f.endswith((".md", ".json", ".csv", ".pdf", ".txt")):
                        fpath = os.path.join(root, f)
                        uri = f"file://{fpath}"
                        if uri not in snapshot_data["documents"]:
                            domain = "GENERAL"
                            for b in _TRACKED_BAGS:
                                if b.name in f or b.name in root:
                                    domain = b.name
                                    break
                            
                            snapshot_data["documents"][uri] = {
                                "uri": uri,
                                "domain": domain,
                                "owner_node": "SYSTEM",
                                "version": "v1.0",
                                "last_modified": datetime.fromtimestamp(os.path.getmtime(fpath), UTC).isoformat(),
                            }

    # 2. Process each tracked bag
    for bag in _TRACKED_BAGS:
        bag_snap = bag.get_hud_snapshot()

        # Add documents owned by this bag's signal manager
        for node_id, uri in bag.signal_manager._result_uris.items():
            if uri not in snapshot_data["documents"]:
                snapshot_data["documents"][uri] = {
                    "uri": uri,
                    "domain": bag.name,
                    "owner_node": node_id,
                    "version": "v1.0",
                    "last_modified": datetime.now(UTC).isoformat(),
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
                    "timestamp": e.timestamp.isoformat() if e.timestamp else datetime.now(UTC).isoformat(),
                })

        snapshot_data["bags"].append({
            "name": bag.name,
            "status": bag.signal_manager.overall_status,
            "nodes": bag_snap["nodes"],
            "links": bag_snap["links"],
            "timeline": raw_events,
        })

    # 3. Merge global chat logs, bag timeline events, and internal bag chats
    unified_chat = list(_CHAT_LOGS)
    seen_chat_hashes = set()
    for log in unified_chat:
        seen_chat_hashes.add(f"{log['sender']}:{log['text']}")

    for bag in _TRACKED_BAGS:
        # Pull internal chats from the SignalManager
        for chat in getattr(bag.signal_manager, "_chat_history", []):
            chat_hash = f"{chat['sender']}:{chat['text']}"
            if chat_hash not in seen_chat_hashes:
                unified_chat.append({
                    "sender": chat["sender"].upper(),
                    "text": f"[{bag.name.upper()}] {chat['text']}" if chat["sender"].upper() == "ORCHESTRATOR" else chat["text"],
                    "timestamp": chat.get("timestamp", datetime.now(UTC).isoformat()),
                })
                seen_chat_hashes.add(chat_hash)

    # 4. Merge timeline events as "system messages"
    for bag_data in snapshot_data["bags"]:
        for event in bag_data["timeline"]:
            unified_chat.append({
                "sender": "SYSTEM",
                "text": f"[{bag_data['name'].upper()}] {event['summary']}",
                "timestamp": event.get("timestamp", datetime.now(UTC).isoformat()),
                "signal": event.get("signal"),
                "node_id": event.get("node_id"),
                "metadata": event.get("metadata", {}),
            })

    with contextlib.suppress(Exception):
        unified_chat.sort(key=lambda x: x.get("timestamp", ""))

    snapshot_data["chat_log"] = unified_chat
    encoded = json.dumps(snapshot_data, default=pydantic_encoder)
    return JSONResponse(content=json.loads(encoded))


@app.post("/api/chat")
def post_chat(msg: ChatMessage):
    """Allows Human or Super-Orchestrator to inject messages into the timeline HUD."""
    timestamp = msg.timestamp or datetime.now(UTC).isoformat()
    log_entry = {"sender": msg.sender.upper(), "text": msg.text, "timestamp": timestamp}
    text = msg.text
    target_bag_name = None
    
    # Handle [TO: BAG] routing
    if text.startswith("[TO: "):
        try:
            end_idx = text.index("]")
            target_bag_name_raw = text[5:end_idx].strip()
            for bag in _TRACKED_BAGS:
                if (bag.name.upper() == target_bag_name_raw.upper() or 
                    bag.name.replace("_", " ").upper() == target_bag_name_raw.upper()):
                    target_bag_name = bag.name
                    break
            text_payload = text[end_idx + 1 :].strip()
            if target_bag_name:
                log_entry["text"] = f"[TO: {target_bag_name.upper()}] {text_payload}"
                text = text_payload
        except ValueError:
            pass

    _CHAT_LOGS.append(log_entry)
    logger.info("[%s] %s", log_entry['sender'], log_entry['text'])
    print(f"\n[{log_entry['sender']}] {log_entry['text']}\n")

    # Record message in relevant Bag(s) so Orchestrators see it
    for bag in _TRACKED_BAGS:
        if target_bag_name and bag.name != target_bag_name:
            continue
        bag.signal_manager.record_chat(msg.sender, text)

    # Resume or Start behavior for Human/Architect messages
    if msg.sender.upper() in ["HUMAN", "ARCHITECT"]:
        for bag in _TRACKED_BAGS:
            # F-REQ-MOD-05: Strict directed routing
            if target_bag_name and bag.name != target_bag_name:
                continue
            
            # F-REQ-MOD-05: "Silent if Idle" for generic broadcasts
            # If no target specified and the bag is IDLE, don't trigger a new job for a simple "status?"
            if not target_bag_name and text.lower().strip() == "status?" and bag.signal_manager.overall_status not in ["RUNNING", "SUSPENDED"]:
                continue

            if bag.signal_manager.overall_status == "SUSPENDED":
                thread_id = bag.signal_manager._active_thread_id
                if thread_id:
                    print(f"[SERVER] Resuming thread {thread_id} in {bag.name} with input...")
                    def resume_task(b=bag, t=thread_id, res=text):
                        b.resume_job(t, human_response=res)
                    threading.Thread(target=resume_task).start()

            elif bag.signal_manager.overall_status not in ["RUNNING", "SUSPENDED"]:
                print(f"[SERVER] Dispatching objective to {bag.name}: {text}")
                def start_task(b=bag, obj=text):
                    b.start_job(objective=obj, inputs={})
                threading.Thread(target=start_task).start()

    return {"status": "ok"}


@app.post("/api/bags/{bag_name}/reset")
def reset_bag_memory(bag_name: str):
    """Explicitly clears the chat memory of a specific bag."""
    target_bag = None
    for bag in _TRACKED_BAGS:
        if bag.name.upper() == bag_name.upper():
            target_bag = bag
            break
    
    if not target_bag:
        raise HTTPException(status_code=404, detail=f"Bag {bag_name} not found")
        
    target_bag.signal_manager.clear_chat_history()
    return {"status": "ok", "message": f"Memory for {bag_name} cleared."}


@app.get("/api/documents/{doc_uri:path}")
def get_document(doc_uri: str):
    """Retrieves the raw content of a document by its URI for HUD previews."""
    content = f"# Artifact: {doc_uri}\n\nContent is being generated by the orchestrator. Please refresh shortly."
    if doc_uri.startswith("file://"):
        filepath = doc_uri.replace("file://", "")
        if filepath.startswith("/seed/"):
            return {
                "uri": doc_uri,
                "content": f"# Seed Document: {filepath}\nThis is an initial seed document to satisfy prerequisites.",
            }
        if os.path.exists(filepath):
            with open(filepath) as f:
                content = f.read()
                return {"uri": doc_uri, "content": content}
    return {"uri": doc_uri, "content": content}


def run_server(port: int = 8000) -> None:
    # Set log_config to None to prevent uvicorn from hijacking our logging settings
    uvicorn.run(app, host="127.0.0.1", port=port, log_level="error", log_config=None)


def start_background_server(port: int = 8000) -> threading.Thread:
    thread = threading.Thread(target=run_server, args=(port,), daemon=True)
    thread.start()
    time.sleep(1)
    return thread
