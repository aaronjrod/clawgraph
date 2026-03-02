# ClawGraph: Node Construction Patterns & Super-Orchestrator Skills

This document defines canonical patterns for building ClawGraph nodes and for Super-Orchestrator behavior. It is intended as both a library reference and a skill file that can be injected into a Super-Orchestrator's context.

---

## Part 1: The ClawNode Contract

Every node in a ClawGraph bag — regardless of what it does internally — must conform to a shared output contract. This is enforced by the `ClawNode` wrapper via a Pydantic base class.

### 1.1 Required Output Schema

```python
from pydantic import BaseModel
from enum import Enum

class Signal(str, Enum):
    DONE               = "DONE"
    FAILED             = "FAILED"
    NEED_INFO          = "NEED_INFO"
    HOLD_FOR_HUMAN     = "HOLD_FOR_HUMAN"
    NEED_INTERVENTION  = "NEED_INTERVENTION"

class ClawOutput(BaseModel):
    signal: Signal
    summary: str                        # Concise accomplishment summary (1-3 sentences).
                                        # This is what the Orchestrator sees. Keep it tight.
    result_uri: str | None = None       # Pointer to the artifact/document produced.
    human_request: str | None = None    # Required when signal == HOLD_FOR_HUMAN.
    error_detail: str | None = None     # Required when signal == FAILED or NEED_INTERVENTION.
    audit_hint: str | None = None       # Optional: Flag that this output warrants deep critique.
                                        # Future: triggers a CritiqueNode.
```

**Rules:**
- `summary` is always required. It is the Orchestrator's only view into what the node did.
- `result_uri` should point to a stored artifact (DB, object store, etc.) — **never** inline raw content into the output.
- If the Orchestrator or Super-Orchestrator needs the full output, they call `audit_node(node_id)`.
- **Signals (audit_hint vs. audit_policy)**: 
    - **`audit_hint` (Worker-led)**: A node self-flags as high-stakes (e.g., "I just generated complex code").
    - **`audit_policy` (Architect-led)**: Defined in node metadata. The Super-Orchestrator can mandate audits (e.g., `audit_policy: { always: true }`) regardless of the node's signal. Authority rests with the Architect.
- `human_request` must be a complete, self-contained message — assume the human has no prior context.

---

## Part 2: Signal Usage Guide

Choosing the wrong signal is the most common source of Orchestrator confusion. Use this guide strictly.

| Signal | When to use | Who handles it |
|---|---|---|
| `DONE` | Task completed successfully. Result is in `result_uri`. | Orchestrator routes to next node. |
| `FAILED` | Node tried, failed, cannot self-recover. Provide `error_detail`. | Orchestrator escalates to Super-Orchestrator. |
| `NEED_INFO` | Node is missing information it needs from an upstream decision-maker. | Orchestrator surfaces to Super-Orchestrator for clarification, then resumes. |
| `HOLD_FOR_HUMAN` | Node requires a specific human decision before proceeding (e.g., approve a shell command, review a diff). | Orchestrator **bypasses** Super-Orchestrator and surfaces `human_request` directly to the user. Thread suspends until human responds. |
| `NEED_INTERVENTION` | State drift, schema mismatch, or unrecoverable orchestration error. The bag itself may be broken. | Orchestrator escalates to Super-Orchestrator for bag repair. |

**Key distinction: `NEED_INFO` vs `HOLD_FOR_HUMAN`**
- Use `NEED_INFO` when a smarter agent (Super-Orchestrator) can answer programmatically.
- Use `HOLD_FOR_HUMAN` when only a human decision is appropriate — approvals, legal, ethical gates.

---

## Part 3: Canonical Node Patterns (The Bag of Agents)

ClawGraph nodes are not just functions; they are **Specialized Agents**. Each node captures a narrow domain of expertise, defined by its `skills.md` files and Architect-led instructions.

### 3.1 The @clawnode Decorator

The primary way to define an agent is via the `@clawnode` decorator.

```python
@clawnode(
    id="regulatory_specialist",
    description="Vets clinical documents against FDA 21 CFR Part 11.",
    skills=["fda_compliance.md", "protocol_benchmarking.md"],
    model="claude-3-5-sonnet", # Specialized reasoning model
    tools=["pdf_parser", "internet_search"]
)
def regulatory_audit(inputs: dict) -> ClawOutput:
    # Logic: The Architect provides the skills context automatically
    ...
```

### 3.2 Simple Task Node

The baseline pattern. One job, one output.

```python
from clawgraph import ClawNode, ClawOutput, Signal

@ClawNode(name="summarize_document", description="Reads a document URI and returns a summary.")
def summarize_document(state: BagState) -> ClawOutput:
    doc = fetch(state["document_archive"]["target_doc"])
    summary_text = llm.summarize(doc)
    uri = store(summary_text)                       # Store result, return pointer
    return ClawOutput(
        signal=Signal.DONE,
        summary=f"Summarized document. Key finding: {summary_text[:120]}...",
        result_uri=uri
    )
```

**Rules:**
- Never return raw text in `result_uri`. Always store first, return the pointer.
- `summary` should capture the *salient finding*, not just confirm the task ran.

---

### 3.3 Node with Human Gate (`HOLD_FOR_HUMAN`)

Use when a dangerous or irreversible action needs explicit approval.

```python
@ClawNode(name="execute_shell_command", description="Runs a shell command after human approval.")
def execute_shell_command(state: BagState) -> ClawOutput:
    command = state["pending_command"]

    if not state.get("shell_approved"):
        return ClawOutput(
            signal=Signal.HOLD_FOR_HUMAN,
            summary="Awaiting human approval to run shell command.",
            human_request=(
                f"The agent wants to run the following shell command:\n\n"
                f"```\n{command}\n```\n\n"
                f"Please approve or reject."
            )
        )

    result = subprocess.run(command, capture_output=True)
    uri = store(result.stdout)
    return ClawOutput(
        signal=Signal.DONE,
        summary=f"Shell command executed successfully. Exit code: {result.returncode}.",
        result_uri=uri
    )
```

**Resumption Logic:**
When the user approves via a UI/Handler:
```python
# The delivery layer calls this:
bag.resume_job(thread_id=state["thread_id"], human_response="approved")
# The node re-runs, state["shell_approved"] is now True, and it proceeds to execution.
```

---

### 3.4 Subgraph with Aggregator Node (Parallel Fan-out)

When work can be parallelized, contain it inside a subgraph. The Orchestrator calls the subgraph as a single unit and receives one signal back. It never sees the individual inner nodes.

```
Subgraph: analyze_codebase
├── Node A: scan_dependencies   ─┐
├── Node B: scan_for_secrets    ─┤──► AggregatorNode ──► ClawOutput(DONE)
└── Node C: lint_check          ─┘
```

- **Aggregator's Job**: Collects internal results and decides the final external signal.
- **Error Detail Rule**: If a parallel branch fails, the Aggregator- **Identification**: `summary` identifies exactly which branch failed (e.g., `"Branch: Site-03 (India) failed CMC check"`).
- **Escalation**: The failure signal is passed to the Orchestrator, which may then route to the Super-Orchestrator for repair.
- **Why?** This allows the Super-Orchestrator to perform targeted repairs/re-runs without resetting the entire subgraph.
- **Role Distinction**: The `summary` tells the **Orchestrator** what happened at a high level for routing; the `error_detail` tells the **Super-Orchestrator** exactly what to fix.

```python
# The aggregator collects all branch results and emits a single summary
@ClawNode(name="aggregator", description="Merges parallel branch results.")
def aggregator(state: SubgraphState) -> ClawOutput:
    results = [state["dep_result"], state["secrets_result"], state["lint_result"]]
    combined_uri = store(results)
    failed = [r for r in results if r["signal"] == "FAILED"]

    if failed:
        # Identify exactly which branches failed for the Super-Orchestrator
        failure_log = ", ".join([f"'{r['node_name']}'" for r in failed])
        return ClawOutput(
            signal=Signal.FAILED,
            summary=f"Parallel analysis partially failed: {len(failed)} of 3 branches failed.",
            error_detail=f"The following branches failed: {failure_log}. Check result_uri for full trace.",
            result_uri=combined_uri
        )

    return ClawOutput(
        signal=Signal.DONE,
        summary="Codebase analysis complete. No secrets found. 3 lint warnings. Dependencies clean.",
        result_uri=combined_uri
    )
```

**Rules:**
- The Orchestrator is notified once — when the subgraph (aggregator) completes.
- Never surface inner node signals directly to the Orchestrator.
- The aggregator is responsible for escalating failures upward with a coherent `error_detail`.

---

### 3.4 Verification Node (Generate-Test-Reinforce)

A test node is just a regular ClawNode. It reads an artifact URI, runs checks, and signals `DONE` (pass) or `FAILED` (fail). The Orchestrator then escalates failures to the Super-Orchestrator for repair.

```python
@ClawNode(name="verify_python_output", description="Runs unit tests against a generated Python module.")
def verify_python_output(state: BagState) -> ClawOutput:
    module_uri = state["document_archive"]["generated_module"]
    module_code = fetch(module_uri)

    test_results = run_tests(module_code, state["test_suite"])

    if not test_results.passed:
        return ClawOutput(
            signal=Signal.FAILED,
            summary=f"Verification failed. {test_results.failure_count} tests failed.",
            error_detail=test_results.failure_log,
            result_uri=store(test_results)
        )

    return ClawOutput(
        signal=Signal.DONE,
        summary=f"All {test_results.total} tests passed.",
        result_uri=store(test_results)
    )
```

**Important:** Test definitions are the developer's responsibility. ClawGraph does not enforce test quality — shallow tests that hallucinate success are a known risk (see Risks in BRS). The Super-Orchestrator should be instructed to write tests that check observable outputs, not just that the node ran.

---

## Part 4: Super-Orchestrator Skills

These are behavioral rules for any agent acting as Super-Orchestrator. They should be injected as a system prompt or skill file.

### 4.1 Discovery-First (Mandatory)

**Before any CRUD operation, always call `get_inventory()` first.**

```
1. Call get_inventory() → receive manifest + node summaries
2. Compare current capabilities against the goal
3. Only then: register_node / update_node / delete_node
```

**Bag-Splitting Heuristic:**
To maintain Orchestrator reasoning quality and context speed:
- **Split at ~50 Nodes**: When a bag grows beyond 50 nodes, the Super-Orchestrator should split the workflow into multiple independent bags.
- **Workflow-Focus**: Each bag should reflect a distinct workflow or a major logical phase. The Orchestrator stays focused on the context within a single bag.

**Why Discovery-First?**
The Orchestrator and bag may already have a node that covers your need. Registering a duplicate causes state drift and wastes tokens. The `ClawBag` will warn you if you attempt CRUD without first querying inventory, but this is advisory — don't rely on it.

### 4.2 Context Discipline

The Super-Orchestrator receives **summaries only** from the Orchestrator during normal operation. This is by design — raw node outputs are stored as URI pointers and are intentionally not surfaced unless requested.

- **Do not ask the Orchestrator to replay raw outputs.** Call `audit_node(node_id)` instead.
- **Trust summaries for routing decisions.** Only audit when a summary seems inconsistent or a node fails unexpectedly.
- **Cold-start is the exception:** When building a bag from scratch, the Super-Orchestrator may need fuller context to design the initial node set. This is expected.

### 4.3 Node Design Principles

When writing a new node, follow these rules:

| Principle | Guidance |
|---|---|
| **Two-Channel Input** | Nodes **must not** be designed to receive raw content. They receive exactly two things: (1) high-level advice/context from the Orchestrator, and (2) URI pointers to documents in the archive. |
| **Meaningful Metadata** | The `metadata` object passed to `register_node` **must** include a `description` field. This is the Orchestrator's *only* view of the node before execution. It must be written by the Super-Orchestrator to be standalone and descriptive. |
| **Single responsibility** | One node, one job. If a node is doing two things, split it. |
| **Contain parallelism** | Parallel work goes inside a subgraph with an aggregator. Never ask the Orchestrator to manage parallel branches directly. |
| **Store, don't inline** | Always store results externally and return a URI. Never return large blobs in `ClawOutput`. |
| **Self-contained `human_request`** | Write `human_request` as if the human has never seen this workflow. Include the context they need to decide. |
| **Descriptive summaries** | `summary` should say what was *found or produced*, not just that the task *ran*. |
| **Orphaned Pointers** | Deleting a node or rolling back a bag **does not** delete its artifacts from the archive. Be aware that state may still reference URIs produced by "ghost" nodes. |
| **Fail loudly** | On failure, always populate `error_detail`. A vague `FAILED` signal without detail forces unnecessary auditing. |

### 4.4 When to Use Each Signal (Super-Orchestrator Decision Tree)

When a node returns a signal, the Super-Orchestrator should respond as follows:

```
DONE              → Continue planning. Read summary. Update phase_history.
FAILED            → Read error_detail. Decide: fix the node, fix the input, or abort.
NEED_INFO         → Answer the clarification. Inject into state. Resume.
HOLD_FOR_HUMAN    → Thread suspends. Wait for `resume_job()` via external handler.
NEED_INTERVENTION → Treat as a bag-level problem. Call get_inventory(). 
                    Inspect state schema. Repair before resuming.
```

### 4.5 Registering a HITL Handler
The Super-Orchestrator or Developer must register a delivery mechanism for `HOLD_FOR_HUMAN` signals.

```python
def my_ui_handler(thread_id, human_request):
    # Send to Slack, WebSocket, or Email
    send_to_user_interface(thread_id, human_request)

bag.register_hitl_handler(my_ui_handler)
```

### 4.6 Cold-Start Sequence

When starting a new project from scratch:

```python
# Step 1: Initialize the bag with a contract
bag = ClawBag(name="my_project", contract=MyBagContract)

# Step 2: Call get_inventory() — even on a fresh bag — to confirm state
inventory = bag.get_inventory()

# Step 3: Register core nodes one at a time, verifying after each
bag.register_node(node_code=..., metadata={...})

# Step 4: Start a test job to verify initial wiring
result = bag.start_job(
    objective="Smoke test: run all nodes against sample input.",
    inputs=sample_inputs,
    max_iterations=3
)

# Step 5: Inspect summaries. Audit any node that looks wrong.
bag.audit_node("node_id_here")
```

### 4.7 Bag Repair (`NEED_INTERVENTION`)

When the Orchestrator emits `NEED_INTERVENTION`:

1. Call `get_inventory()` to get the current manifest.
2. Read `error_detail` from the signal payload.
3. Identify the schema mismatch or state drift.
4. Either: update the broken node (`update_node`), or patch the global state schema.
5. Optionally: `rollback_bag(version)` to revert to a known-good manifest version (experimental).
6. Re-run the job from the last good checkpoint.

---

## Part 5: What the Orchestrator Sees (Summary View)

To reinforce Part 4.2: the Orchestrator's view of the bag is intentionally narrow. At any given turn, it sees:

- The current `objective`
- The `bag_manifest` (node names, descriptions, summaries — no raw code)
- The `phase_history` (list of accomplishment summaries from completed phases)
- The current signal from the most recently completed node

It does **not** see:
- Raw tool outputs
- Full node source code
- The contents of `document_archive` entries (only their keys/URIs)

This is the mechanism that keeps the Orchestrator's context lean. The Super-Orchestrator is the only actor that fetches full artifacts, and only when needed via `audit_node()`.

## Part 6 - Deployment Patterns

### 6.1 Persistent Heartbeat / Cron
For long-running autonomous operations, ClawGraph supports a **Persistent Heartbeat** pattern:
- **Automation**: A wrapper process (Cron or a while-loop) periodically calls `start_job()` with a recurring goal (e.g., "Monitor inbox and handle new property leads").
- **State Continuity**: Each heartbeat uses the same `thread_id` or pulls the latest `checkpoint_id` to maintain continuity between runs.
- **Durable Memory**: The shared Document Archive ensures the agent remembers context from previous heartbeats without saturating the current context window.

#### Heartbeat Example (Python)
```python
# scheduler.py
while True:
    # 1. Pull latest checkpoint/thread from persistence
    thread_id = "agent_heartbeat_001"
    
    # 2. Start (or resume) the job with the recurring objective
    # ClawGraph handles the context pruning/summarization internally.
    result = bag.start_job(
        objective="Analyze latest leads and log to CRM",
        thread_id=thread_id,
        max_iterations=5
    )
    
    # 3. Handle signals (Escalations go to Super-Orchestrator process)
    if result.signal == "NEED_INTERVENTION":
         escalate_to_admin(result.error_detail)
         
    time.sleep(3600) # Wait for next cron cycle
```
---

## Part 7: Mission Control Data Schema (`get_hud_snapshot`)

To build the "super simple graph visualizer," the library emits a merged snapshot of the bag's topology and the transient signal state.

### 7.1 Snapshot JSON Shape
```json
{
  "thread_id": "job_abc_123",
  "nodes": [
    {
      "id": "node_001",
      "name": "classify_intent",
      "status": "DONE",
      "summary": "User wants to query property taxes.",
      "signal": "DONE",
      "result_uri": "s3://archive/job_abc/node_001.json",
      "implicit_links": []
    },
    {
      "id": "node_002",
      "name": "search_tax_db",
      "status": "RUNNING",
      "summary": null,
      "signal": null,
      "result_uri": null,
      "implicit_links": ["node_001"] 
    }
  ],
  "links": [
    { "source": "orchestrator", "target": "node_001", "type": "topology" },
    { "source": "node_001", "target": "node_002", "type": "data_flow" }
  ]
}
```

### 7.2 Link Types & Visualization
The `links` array in the snapshot contains two distinct types of relationships:

1.  **Topology Links (`topology`)**: These are the **explicit** edges defined in the underlying **LangGraph** graph structure. In the hub-and-spoke model, these primarily connect the Orchestrator to worker nodes. In subgraphs, these represent the static wiring between inner nodes.
2.  **Data Flow Links (`data_flow`)**: These are **implicit** links inferred by the library. If Node B consumes a `result_uri` produced by Node A, the library populates `implicit_links: ["node_001"]` for Node B. 

**Visualization Tip**: Render topology links (LangGraph edges) as solid lines to show the structural hierarchy, and data-flow links (URI dependencies) as dashed/colored lines to show how information is actually moving through the bag.

---

## Appendix: Signal Quick Reference

```
DONE               ✅  Work complete. result_uri has the artifact.
FAILED             ❌  Unrecoverable failure. error_detail is required.
NEED_INFO          ❓  Needs upstream clarification. Super-Orchestrator answers.
HOLD_FOR_HUMAN     🧑  Human decision required. Orchestrator bypasses SO. Thread suspends.
NEED_INTERVENTION  🚨  Bag/state is broken. Super-Orchestrator repairs before resuming.
```