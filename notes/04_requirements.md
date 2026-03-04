# ClawGraph Requirements Specification

## 1. Project Overview
ClawGraph is a next-generation agent orchestration library designed to reconcile the tension between **unconstrained agency** (OpenClaw) and **deterministic structure** (LangGraph). It introduces a signal-based, decentralized model that allows autonomous agents to manage other agents while maintaining robust observability, safety, and token efficiency.

### Core Philosophy
- **Agents managing agents**: High-level orchestrators govern the flow, while specialized agents execute tasks.
- **Signal-based coordination**: Transition from fixed DAGs to event-driven signals.
- **Dynamic Workflows**: Enable Just-In-Time (JIT) creation and modification of agent capabilities.

---

## 2. Architectural Tiers

### 2.1 Super-Orchestrator (The Architect)
- **Role**: High-level intelligence (e.g., Claude Code, Antigravity, OpenClaw).
- **Responsibilities**: 
    - CRUD operations on the "Bag of Nodes".
    - Defining the global objective.
    - Debugging and fixing the workflow when it fails (Generate-Test-Reinforce).
    - Managing the relationship with the Orchestrator.

### 2.2 Orchestrator (The Project Manager / Director)
- **Role**: A "simple" LLM-based agent or runtime that executes the workflow.
- **Responsibilities**:
    - Monitoring the "Bag of Nodes".
    - Routing execution based on signals from nodes.
    - Aggregating outputs and generating phase summaries for the Super-Orchestrator.
    - Maintaining the "Versioned Manifest" of the bag (via the BagManager).

### 2.3 Bag of Nodes (The Capabilities Registry)
- **Role**: A flat or hierarchical collection of addressable LangGraph nodes/subgraphs.
- **Features**:
    - **Individual Addressability**: Nodes can be called independently of a graph structure.
    - **Signal-on-Done**: Nodes emit completion signals: `DONE`, `FAILED`, `PARTIAL`, `NEED_INFO`, `HOLD_FOR_HUMAN`, `NEED_INTERVENTION`.
    - **Agent Cards**: Each node exposes metadata (JSON-LD) describing inputs, outputs, and function summary.

---

## 3. Key Functional Requirements

### 3.1 Signal-Based Orchestration
- The system must support asynchronous event propagation.
- **Node-Managed Parallelism**: The Orchestrator calls a single node/subgraph; internal fan-out/fan-in and synchronization are managed within that node's internal graph logic (using Aggregator Nodes), returning a single signal to the Orchestrator.
- **Discovery-First Flow**: The Super-Orchestrator must query the Bag Inventory before initiating CRUD operations to prevent redundant implementations.
- Nodes must emit signals to a central Hub (Orchestrator) for routing decisions. Supported signals: `DONE`, `FAILED`, `PARTIAL`, `NEED_INFO`, `HOLD_FOR_HUMAN`, `NEED_INTERVENTION`.

### 3.2 Dynamic CRUD Operations
- The library must provide APIs for adding, reading, updating, deleting, and listing nodes in the bag at runtime.
- **Auto-Versioning**: The system must automatically increment the manifest version on every successful CRUD commitment.
- Support for rebuilding and re-compiling the execution graph for every "job".

### 3.3 Phase-Based Execution & Summarization
- Workflows must be divisible into "Phases" (subgraphs).
- **Integrated Summarization**: Each node/phase must generate an **Accomplishment Summary** as part of its primary output (ideally within the same LLM call using structured output/Pydantic schemas) to minimize latency and token usage.
- Summaries should prioritize salient points and findings to minimize context growth for the Orchestrator/Super-Orchestrator.
- **On-Demand Auditing**: Support for retrieving full raw traces (pointers) for any node at any time. Transitions between node disclosure tiers are triggered by `audit_hint` (node-reported) and `audit_policy` (orchestrator-defined) mechanisms.
    - **Self-Hardening / Red-Teaming**: The audit system should support re-running nodes against "poisoned" or adversarial inputs to test the robustness of the node's internal logic and guardrails.

### 3.4 State Management & Contracts
- Use pointers/references to documents instead of passing raw content between nodes.
- Global state should be minimal, consisting of metadata, instructions, and pointers to external resources.
- **Bag Contracts**: Define strict input/output schemas per bag to prevent state drift.
- **Multi-Domain Document Tagging**: Enable artifacts to be visible across sovereign workspaces with strict owner-domain enforcement (B-REQ-13).
- **Escalation**: The Orchestrator must escalate schema drift to the Super-Orchestrator for repair.

---

## 4. Technical Requirements

### 4.1 LangGraph Wrapper
- The library must wrap LangGraph's API to provide the "Bag of Nodes" abstraction.
- Support for `Command` and `Send` APIs for "edgeless" routing via the Orchestrator spoke.

### 4.2 Token Efficiency & Governance
- Automatic pruning of older tool outputs and intermediate logs.
- Hierarchical state management to prevent "context saturation".
- **Iteration Limits**: Enforce a "Max Iteration" hyperparameter to cap optimization loops.

### 4.3 Versioning & Persistence
- Maintain a versioned manifest of the node bag (auto-bumped).
- Ability to roll back the bag and global state to a previous manifest version.
- **ACID Persistence**: The session store must be ACID-compliant to prevent state corruption.
    - **Development**: SQLite is the default for local development and single-process execution.
    - **Production**: Support for Postgres or MySQL for multi-process concurrency, networked access, and high-volume analytics.

---

## 5. Monitorability & Security

### 5.1 Visualization
- Provide a "Mission Control" trace view showing active nodes, signals, and summaries in real-time.
- Support for a simple graph visualizer for human oversight.

### 5.2 Human-in-the-Loop (HITL)
- **Signal-Based Gating**: Dangerous actions or review points are implemented via the `HOLD_FOR_HUMAN` signal.
- **Orchestrator Suspension**: Upon receiving `HOLD_FOR_HUMAN`, the Orchestrator shall suspend the thread (checkpointing state) and surface a `human_request` payload.
- **Resumption**: The system shall support a registered `hitl_handler` and `resume_job` API for asynchronous decision injection.

### 5.3 Verification Loop
- Support for "Tests as Nodes" within the bag.
- Capability for the Super-Orchestrator to run automated verification cycles (Generate-Test-Reinforce).

---

## 6. Risks & Limitations
- **Evaluation Gap**: Large-scale, automated evaluation is left as an exercise for the developer. ClawGraph provides the infrastructure for "Tests as Nodes", `audit_hint`, and `audit_policy` signals, but does not mandate specific evaluation models, prioritizing developer flexibility over brittle system-defined tests.
- **Lossy Coordination**: Summaries may omit subtle failure points (mitigated by pointer-based auditing, `audit_hint`, and `audit_policy`).
- **Scale Constraints**: Large bags (>50 nodes) impact Orchestrator reasoning. The recommended mitigation is to split complex workflows into multiple independent bags/subgraphs rather than implementing auto-discovery in v1.
