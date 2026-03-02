# Functional Requirement Specifications (FRS): ClawGraph

## 1. System Overview
ClawGraph is a Python library that wraps LangGraph to provide a signal-based, decentralized orchestration engine. It facilitates a hierarchical relationship between a **Super-Orchestrator** (Architect), an **Orchestrator** (Director), and a **Bag of Nodes** (Capabilities).

## 2. Functional Requirements

### 2.1 "Bag of Nodes" Management (CRUD)
- **F-REQ-1 (Dynamic Registration)**: The system shall allow the addition of nodes or subgraphs to a "Bag" at runtime.
- **F-REQ-2 (Edgeless Discovery)**: Nodes shall be individually addressable by name or ID without requiring pre-defined edges.
- **F-REQ-3 (Manifest Management)**: The system shall maintain a JSON-LD manifest of all nodes in a bag, including their descriptions and input/output schemas.
- **F-REQ-4 (Auto-Versioning)**: The system shall automatically increment the manifest version upon any successful CRUD operation on the bag.
- **F-REQ-5 (Graph Re-compilation)**: The system shall support on-the-fly compilation of StateGraphs whenever the bag is modified or a new job is initiated.

### 2.2 Signal-Based Orchestration
- **F-REQ-6 (Signal Taxonomy)**: Each node shall emit one of the following base signals:
    - `DONE`: Task completed successfully.
    - `FAILED`: Task failed irrecoverably.
    - `NEED_INFO`: Node is paused, waiting for clarification from any upstream actor.
    - `HOLD_FOR_HUMAN`: Node is gated on a specific human decision (e.g., approve shell/diff).
    - `NEED_INTERVENTION`: State drift or unrecoverable orchestration error; escalates to Super-Orchestrator.
- **F-REQ-7 (Hub-and-Spoke Routing)**: Finished nodes shall return control and a payload to the Orchestrator (the Hub), which determines the next activation based on the signal.
- **F-REQ-8 (Internal Parallelism)**: Parallel execution (fan-out/fan-in) shall be managed *internally* by the called node/subgraph. The Orchestrator interaction remains a 1-to-1 call-and-response pattern.

### 2.3 Context & Memory Management
- **F-REQ-9 (Integrated Summaries)**: Nodes shall generate an accomplishment summary as part of their structured output (e.g., via a Pydantic schema used in the primary LLM call) rather than a secondary call.
- **F-REQ-10 (Pointer-Based State)**: The global state shall store references/pointers to documents and artifacts rather than raw text blobs.
- **F-REQ-11 (Selective Memory Pruning)**: The system shall automatically remove raw tool outputs from the active context once a phase summary is generated.
- **F-REQ-12 (Mission Control View)**: Expose a telemetry stream from the Signal Manager that can be rendered into a live status/trace visualizer.

### 2.4 Lead-Teammate Interaction (Super-Orchestrator Support)
- **F-REQ-13 (On-Demand Auditing)**: The system shall allow the Super-Orchestrator to retrieve a pointer-based trace of raw outputs (Audit Log) for ANY node at any time.
- **F-REQ-14 (Proactive Security Hardening)**: The system shall support **Injection Testing** (re-running nodes with mutated/adversarial inputs) as a first-class security workflow to detect privilege escalation and rogue behavior.
- **F-REQ-15 (Grounding & Discovery)**: The system shall provide a "Bag-Inventory" tool for the Super-Orchestrator to query all current node summaries and metadata before initiating CRUD operations.
- **F-REQ-16 (Generate-Test-Reinforce Loop)**: The system shall support "Verification Nodes" that can trigger rollbacks or code-edits by the Super-Orchestrator upon task failure.
- **F-REQ-17 (Loop Governance)**: The system shall enforce a configurable maximum iteration limit (Hyperparameter) for the optimization loop, escalating to the user upon exhaustion.
- **F-REQ-18 (State Drift Escalation)**: On state schema mismatch or drift, the Orchestrator shall emit a `NEED_INTERVENTION` signal to the Super-Orchestrator for repair.

### 2.5 Governance & Safety
- **F-REQ-19 (Bag Contract)**: Each bag shall define a strict schema for its inputs and outputs to ensure node compatibility and prevent state drift.
- **F-REQ-20 (Human-in-the-Loop)**: HITL is implemented via the `HOLD_FOR_HUMAN` signal. Nodes requiring approval shall include a `human_request` payload.
    - **Suspension**: The Orchestrator shall checkpoint the state and suspend the thread (non-blocking).
    - **Hand-off**: The system shall call a registered `hitl_handler(thread_id, human_request)` callback to surface the request to the delivery layer (UI/Slack/Email).
    - **Resumption**: The system shall provide a `resume_job` API to inject the human's response and restart the thread from the checkpoint.
- **F-REQ-21 (Audit Triggers)**: 
    - **Worker-Led**: The `ClawOutput` schema shall include an optional `audit_hint` field to signal that a result warrants deeper critique.
    - **Architect-Led**: The system shall support persistent `audit_policy` rules in node metadata that mandate auditing under specific conditions (e.g., `always: true`).
- **F-REQ-22 (Cold-Start Bootstrap)**: The system shall support initializing a `ClawBag` from a fully blank state. The Super-Orchestrator must be able to call `get_inventory()` on an empty bag (returning an empty manifest) and incrementally build the bag via sequential `register_node` calls before any job is started.
- **F-REQ-23 (HUD Snapshot)**: The system shall provide a `get_hud_snapshot()` API that returns a merged JSON view of the Bag Manifest (topology) and the Signal Manager's live status (node status, last signal, summaries) for real-time visualization.

## 3. Interfaces

### 3.1 Internal (Library) Interface
- `ClawBag`: The main container for nodes. owns the `Manifest` and `BagManager`.
- `ClawNode`: The wrapper for LangGraph nodes (Instrumentation + Schema).
- `ClawOrchestrator`: The director logic that consumes signals and inventory.
- `SignalManager`: Independent telemetry module tracking real-time node status.

### 3.2 External (API) Interface
- `register_node(node_code, metadata)`
- `update_node(node_id, new_code)`
- `delete_node(node_id)`
- `rollback_bag(version)` -> Reverts the bag manifest and compiled state to a previous version (Experimental).
- `get_inventory()` -> Returns the current manifest and node summaries.
- `start_job(objective, inputs, max_iterations=5)`
- `resume_job(thread_id, human_response)` -> Injects the response and resumes a suspended thread.
- `register_hitl_handler(callback)` -> Registers a callback for `HOLD_FOR_HUMAN` events.
- `audit_node(node_id)` -> Returns raw trace pointers for a node.
- `get_hud_snapshot()` -> Returns the merged manifest and signal state for UI rendering.
- `get_summary(thread_id)`

## 4. Technical Constraints
- Built on top of **LangGraph v0.2+**.
- Compatible with **Claude Code/OpenClaw** tool-calling patterns.
- Optimized for **500k+ context window models** for the Orchestrator role.
