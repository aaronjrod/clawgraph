import threading
import time
from typing import Any

import uvicorn
from fastapi import FastAPI
from fastapi.responses import HTMLResponse

app = FastAPI()

# Global reference to allow polling
_ACTIVE_BAG: Any = None


def set_active_bag(bag: Any) -> None:
    global _ACTIVE_BAG
    _ACTIVE_BAG = bag


@app.get("/")
def get_index() -> HTMLResponse:
    with open("examples/live_integration/index.html") as f:
        html = f.read()
    return HTMLResponse(content=html)


@app.get("/api/snapshot")
def get_snapshot() -> dict[str, Any]:
    global _ACTIVE_BAG
    if _ACTIVE_BAG:
        return _ACTIVE_BAG.get_hud_snapshot()
    return {"nodes": []}


def run_server(port: int = 8000) -> None:
    uvicorn.run(app, host="127.0.0.1", port=port, log_level="error")


def start_background_server(port: int = 8000) -> threading.Thread:
    thread = threading.Thread(target=run_server, args=(port,), daemon=True)
    thread.start()
    time.sleep(1)  # Give server time to boot
    return thread
