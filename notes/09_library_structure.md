# Proposed Library Structure (ClawGraph)

To handle the complexity of hierarchical orchestration and ensure maintainability, the library is organized into specialized modules corresponding to the Sovereign Workspace tiers.

## 📂 Projected Directory Structure

```text
clawgraph/
├── __init__.py
├── core/                   # 🧱 Foundation & Base Schemas (Phase 1)
│   ├── __init__.py
│   ├── models.py           # ClawOutput, Pydantic Base Models
│   ├── signals.py          # Signal Enum, SignalManager logic
│   └── exceptions.py       # Custom ClawGraph errors
│
├── orchestrator/           # 🧠 Tactical Hub (Phase 2)
│   ├── __init__.py
│   ├── hub.py              # Central Orchestrator node logic
│   ├── graph.py            # LangGraph topology & Lazy Compilation
│   └── prompts.py          # Orchestrator & Aggregator system prompts
│
├── bag/                    # 👜 Bag & Node Management (Phase 1 & 3)
│   ├── __init__.py
│   ├── manager.py          # BagManager (Manifest versioning)
│   ├── node.py             # @ClawNode decorator & registration
│   └── inventory.py        # get_inventory() logic
│
├── storage/                # 💾 Persistence & Archive (Phase 5)
│   ├── __init__.py
│   ├── checkpointers.py    # Sqlite/Postgres LangGraph persistence
│   └── archive.py          # Document Archive (result_uri handling)
│
├── telemetry/              # 📡 HUD & Observability (Phase 4)
│   ├── __init__.py
│   ├── hud.py              # get_hud_snapshot() API
│   └── links.py            # Implicit Linkage scanner (data-flow)
│
└── skills/                 # 📜 Lead-Teammate Instructions (Phase 3)
    ├── discovery.md        # Discovery-First protocol
    ├── audit.md            # Deep auditing & AuditPolicy rules
    └── repair.md           # NEED_INTERVENTION repair steps
```

## 🛠️ Module Breakdown

### `core/`
This is the low-level contract layer. Every node and orchestrator depends on these schemas. It ensures that the "handshake" between components remains consistent across versions.

### `orchestrator/`
The most complex part of the library. It contains the LangGraph-specific code. By isolating it in its own folder, we can swap orchestration backends (e.g., to a custom state machine) without breaking the rest of the library.

### `bag/`
Handles the dynamic catalog of capabilities. This module is responsible for keeping the "Sovereign Workspace" organized and preventing state drift via manifest versioning.

### `storage/`
Decouples the logic from the database. It handles the "ACID" requirement by ensuring checkpoints are saved correctly at every intersection.

### `telemetry/`
The "read-only" visibility layer. It scans the state to produce the HUD snapshot but never modifies the bag's execution.

---
**Ref**: [05_ARCHITECTURE.md](file:///Users/aaronrodrigues/projects/clawgraph/notes/05_ARCHITECTURE.md), [03_FRS.md](file:///Users/aaronrodrigues/projects/clawgraph/notes/03_FRS.md)
