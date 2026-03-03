# Functional Requirement Specifications (FRS): ClawGraph

## 1. System Overview
ClawGraph is a Python library that wraps LangGraph to provide a signal-based, decentralized orchestration engine. It facilitates a hierarchical relationship between a **Super-Orchestrator** (Architect), an **Orchestrator** (Director), and a **Bag of Nodes** (Capabilities).

## 2. Functional Requirements

### 2.1 "Bag of Nodes" Management (CRUD)
- **F-REQ-1 (Dynamic Registration)**: The system shall allow the addition of nodes or subgraphs to a "Bag" at runtime.
- **F-REQ-2 (Edgeless Discovery)**: Nodes shall be individually addressable by name or ID without requiring pre-defined edges.
- **F-REQ-3 (Manifest Management)**: The system shall maintain a JSON-LD manifest of all nodes in a bag, including their descriptions, input/output schemas, and optional `requires` (artifact prerequisites).
- **F-REQ-4 (Auto-Versioning)**: The system shall automatically increment the manifest version upon any successful CRUD operation on the bag.
- **F-REQ-5 (Graph Re-compilation)**: The system shall support on-the-fly compilation of StateGraphs whenever the bag is modified or a new job is initiated.

### 2.2 Signal-Based Orchestration
- **F-REQ-6 (Node Output Signals)**: Each node shall emit one of the following signals to the Orchestrator via `ClawOutput`:
    - `DONE`: Task completed successfully.
    - `FAILED`: Task failed irrecoverably. **MUST** include a structured `error_detail` object.
    - `NEED_INFO`: Node is paused, waiting for clarification from any upstream actor (Super-Orchestrator or User).
    - `HOLD_FOR_HUMAN`: Node is gated on a specific human decision (e.g., approve shell execution or document diff).
    - `NEED_INTERVENTION`: State drift or unrecoverable orchestration error; escalates to Super-Orchestrator for repair.

### 2.2.1 Error Taxonomy (`error_detail`)
- **F-REQ-12.1 (Failure Classification)**: Every `FAILED` signal shall include a `failure_class` from the following enum:
    - `LOGIC_ERROR`: Flaw in node implementation or reasoning.
    - `SCHEMA_MISMATCH`: Input/Output does not match the Bag Contract or Tool schema.
    - `TOOL_FAILURE`: External API or CLI tool returned an error or timed out.
    - `GUARDRAIL_VIOLATION`: Security policy blocked a requested action.
    - `SYSTEM_CRASH`: Unhandled exception caught by the Orchestrator.
- **F-REQ-12.2 (Standard Metadata)**: Failure payloads shall include `expected` vs `actual` values (where applicable) and optionally a `suggested_fix_hint` (plain language) to ground the Super-Orchestrator's repair logic.

### 2.2.2 Signal Escalation & Auto-Recovery
- **F-REQ-15.1 (Deterministic Escalation)**: The Orchestrator shall implement a time-and-retry-based escalation path:
    - `NEED_INFO` signals shall have a configurable **TTL** and **Retry Budget**.
    - Upon budget exhaustion (timeout or max retries), the Orchestrator shall automatically promote the signal to `NEED_INTERVENTION`.
- **F-REQ-15.2 (Exception Interception)**: The Orchestrator shall wrap all node executions in an exception handler. If a node crashes without returning a `ClawOutput`, the Orchestrator shall synthesize a `FAILED` signal with a `SYSTEM_CRASH` failure class and include the traceback in the `error_detail`.

### 2.2.3 Orchestrator Status Events
To provide high-fidelity monitoring, the Orchestrator emits status events directly to the Signal Manager. These are NOT part of the node contract:
- **`STALLED`**: Emitted when a node's `requires` prerequisites are not yet met in the `document_archive`.
- **`RUNNING`**: Emitted when a node has successfully started execution.
- **`RESOLVING`**: Emitted when the Orchestrator is performing prerequisite re-evaluation.
- **F-REQ-7 (Hub-and-Spoke Routing)**: Finished nodes shall return control and a payload to the Orchestrator (the Hub), which determines the next activation based on the signal.
- **F-REQ-8 (Signal Bubble / Aggregation)**: Parallel execution (fan-out/fan-in) managed via subgraphs shall act as a "Signal Bubble." The Orchestrator only receives a single completion signal from the subgraph's **Aggregator Node**. Individual branch signals (`FAILED`, `DONE`) are consumed by the Aggregator and merged into the final `ClawOutput`.

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

### 2.6 Timeline & Observability
- **F-REQ-24 (Event Log API)**: The system shall provide a `get_timeline(thread_id)` API that retrieves a durable stream of lifecycle events from the Session DB.
- **F-REQ-25 (Event Schema)**: Every timeline event shall follow a standardized schema: `{event_id, timestamp, node_id, signal, summary, duration_ms, tier, metadata}`.
- **F-REQ-26 (HITL Context Window)**: When a `HOLD_FOR_HUMAN` signal is emitted, the system shall automatically package the preceding $N$ events (default 5) into the intervention payload to provide lead-up context.
- **F-REQ-27 (Timeline Seek & Inspect)**: The system shall support retrieving the full archival state (Tier 3) associated with any historical event's `result_uri` to facilitate retrospective auditing.
- **F-REQ-28 (Prerequisite Re-evaluation)**: The Orchestrator shall re-evaluate the `STALLED` queue immediately after every `DONE` signal. Any nodes whose `requires` list is now satisfied by the updated `document_archive` shall be moved to the `READY` queue.

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
- `get_timeline(thread_id)` -> Returns a durable stream of lifecycle events from the Session DB.
- `get_summary(thread_id)`

## 4. Technical Constraints
- Built on top of **LangGraph v0.2+**.
- Compatible with **Claude Code/OpenClaw** tool-calling patterns.
- Optimized for **500k+ context window models** for the Orchestrator role.
