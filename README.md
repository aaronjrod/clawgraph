# ClawGraph 👜

**ClawGraph** is a hierarchical agent orchestration framework built on [LangGraph](https://github.com/langchain-ai/langgraph). It introduces the **Sovereign Workspace** model, enabling a high-level "Super-Orchestrator" (Architect) to manage a dynamic "Bag of Nodes" through a tactical, signal-based runtime.

## 🧠 The Sovereign Workspace
ClawGraph partitions agentic labor into three distinct tiers:
- **The Lead Teammate (Super-Orchestrator)**: The "Coder" who builds, audits, and repairs the bag of capabilities.
- **The Orchestrator (Runtime)**: The "Tactical Director" who manages routing, signal state, and context pruning.
- **The Bag of Nodes (Library)**: A collection of task-specific nodes that perform atomic units of work.

## ✨ Key Features
- **Signal-Based Orchestration**: Routing driven by standardized signals (`DONE`, `FAILED`, `NEED_INFO`, `HOLD_FOR_HUMAN`, `NEED_INTERVENTION`).
- **3-Tier Progressive Disclosure**: Maintains token efficiency by loading only metadata for the Orchestrator, while keeping code and raw results available for deep audits.
- **Lazy Compilation**: Execution graphs are compiled on-demand only when the bag's manifest version changes.
- **Discovery-First Protocols**: Enforces a "query-before-edit" workflow for the Super-Orchestrator to prevent capability drift.
- **Mission Control HUD**: Real-time JSON-LD snapshots of topology and transient state, including implicit data-flow links.

## 📂 Project Organization
Initial project specifications and implementation plans are located in the `notes/` directory:

1. [01_PLAN.md](notes/01_PLAN.md): Original project goals and brainstorming.
2. [02_BRS.md](notes/02_BRS.md): Business requirements and success metrics.
3. [03_FRS.md](notes/03_FRS.md): Functional specs and API definitions.
4. [05_ARCHITECTURE.md](notes/05_ARCHITECTURE.md): Technical deep-dive into the hub-and-spoke model.
5. [06_patterns.md](notes/06_patterns.md): Canonical node design and Super-Orchestrator skills.
6. [08_walkthrough.md](notes/08_walkthrough.md): Comprehensive project walkthrough and implementation roadmap.
7. [09_library_structure.md](notes/09_library_structure.md): Projected file and module organization.

## 🛠️ Implementation Roadmap
We are currently moving through the following phases:
- **Phase 1**: Foundation & State (Schemas & Managers)
- **Phase 2**: Tactical Hub (LangGraph Orchestrator)
- **Phase 3**: The Architect's Tools (Node CRUD & Auditing)
- **Phase 4**: HUD & Telemetry (Observability)
- **Phase 5**: Production & Hardening (Persistence & HITL)

## 📜 License
This project is licensed under the **Apache License 2.0**.
