# ClawGraph: Node Construction Patterns & Super-Orchestrator Skills

This document defines canonical patterns for building ClawGraph nodes and for Super-Orchestrator behavior. It is intended as both a library reference and a skill file that can be injected into a Super-Orchestrator's context.

---

## Part 1: The ClawNode Contract

Every node in a ClawGraph bag — regardless of what it does internally — must conform to a shared output contract. This is enforced by the `ClawNode` wrapper via a Pydantic base class.

### 1.1 Required Output Schema

> **Canonical Definition**: [12_clawoutput_spec.md](file:///Users/aaronrodrigues/projects/clawgraph/notes/12_clawoutput_spec.md)
>
> The full Pydantic model with validators, sub-models, and design rationale lives in the canonical spec. Below is a simplified quick-reference for use in pattern examples.

```python
from clawgraph.core.models import ClawOutput, Signal

# Quick-Reference: Routing Envelope (what the Orchestrator sees)
# ──────────────────────────────────────────────────────────────
# signal: Signal                       — Terminal signal. Drives all routing.
# node_id: str                         — ID of the emitting node.
# orchestrator_summary: str            — Terse, routing-relevant (1-2 sentences).
# result_uri: str | None               — Pointer to artifact. REQUIRED for DONE/PARTIAL.
# audit_hint: bool | None              — True = self-flag for critique. None ≠ False.
# orchestrator_synthesized: bool       — Provenance marker (Orchestrator constructed this).
#
# Detail Payload (persisted to timeline, not routed over)
# ──────────────────────────────────────────────────────────────
# operator_summary: str | None         — Human-readable summary for HUD. Falls back to orchestrator_summary.
# error_detail: ErrorDetail | None     — Required on FAILED/PARTIAL/NEED_INTERVENTION.
# info_request: InfoRequest | None     — Required on NEED_INFO.
# human_request: HumanRequest | None   — Required on HOLD_FOR_HUMAN.
# continuation_context: dict | None    — Opaque state for suspended node resumption.
# started_at / completed_at: datetime  — Self-reported timing.
# schema_version: int                  — For migration safety.
# output_id: str                       — UUID for idempotency on replay.
```

**Rules:**
- `orchestrator_summary` is always required. It is the Orchestrator's only view into what the node did.
- `result_uri` should point to a stored artifact (DB, object store, etc.) — **never** inline raw content into the output. Required for `DONE` and `PARTIAL`.
- If the Orchestrator or Super-Orchestrator needs the full output, they call `audit_node(node_id)`.
- **Signals (audit_hint vs. audit_policy)**: 
    - **`audit_hint` (Worker-led)**: A boolean. `True` = self-flag for audit. `None` = no preference (defer to policy). `False` = explicitly opted out.
    - **`audit_policy` (Architect-led)**: Defined in node metadata. The Super-Orchestrator can mandate audits (e.g., `audit_policy: { always: true }`) regardless of the node's signal. **Policy > Hint** (F-REQ-27).
- `human_request` must be a complete, self-contained `HumanRequest` — assume the human has no prior context.

---

## Part 2: Signal Usage Guide

Choosing the wrong signal is the most common source of Orchestrator confusion. Use this guide strictly.

| Signal | When to use | Who handles it |
|---|---|---|
| `DONE` | Task completed successfully. Result is in `result_uri`. | Orchestrator routes to next node. |
| `FAILED` | Node tried, failed, cannot self-recover. Provide `error_detail`. | Orchestrator escalates to Super-Orchestrator. |
| `PARTIAL` | Subgraph/Phase completed but with mixed results (e.g., 2/3 branches passed). Provide breakdown in `error_detail`. | Orchestrator decides whether to proceed or remediate. |
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
from clawgraph.core.models import ClawOutput, Signal
@ClawNode(name="summarize_document", description="Reads a document URI and returns a summary.")
def summarize_document(state: BagState) -> ClawOutput:
    doc = fetch(state["document_archive"]["target_doc"])
    summary_text = llm.summarize(doc)
    uri = store(summary_text)                       # Store result, return pointer
    return ClawOutput(
        signal=Signal.DONE,
        node_id="summarize_document",
        orchestrator_summary=f"Summarized document. Key finding: {summary_text[:120]}...",
        result_uri=uri
    )
```

**Rules:**
- Never return raw text in `result_uri`. Always store first, return the pointer.
- `orchestrator_summary` should capture the *salient finding*, not just confirm the task ran.

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
            node_id="execute_shell_command",
            orchestrator_summary="Awaiting human approval to run shell command.",
            human_request=HumanRequest(
                message=(
                    f"The agent wants to run the following shell command:\n\n"
                    f"```\n{command}\n```\n\n"
                    f"Please approve or reject."
                ),
                action_type="approve_shell"
            )
        )
    result = subprocess.run(command, capture_output=True)
    uri = store(result.stdout)
    return ClawOutput(
        signal=Signal.DONE,
        node_id="execute_shell_command",
        orchestrator_summary=f"Shell command executed successfully. Exit code: {result.returncode}.",
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

### 3.4 Subgraph with Aggregator Node (The Signal Bubble)

When work is parallelized, it is contained within a **Signal Bubble**. The Orchestrator calls the subgraph as a single unit and receives **one** signal back. 

- **Aggregator's Job**: Collects all internal results (from the Signal Manager or inner state) and decides the final external signal (`DONE`, `FAILED`, or `PARTIAL`).
- **Partial Commit Policy**: Respects `eager` (commit branch results immediately) or `atomic` (defer all to bubble completion). Eager commits allow STALLED consumers to unblock mid-bubble.
- **Abstraction Layer**: It produces a rolled-up summary for the Orchestrator, effectively hiding the internal noise while the system-level timeline/audit logs contain the full-fidelity branch data.

```python
# Aggregator logic: Consolidating parallel signals into a PARTIAL outcome
@ClawNode(name="aggregator", description="Merges parallel branch results.")
def aggregator(state: SubgraphState) -> ClawOutput:
    # 1. Collect results from all parallel branches
    results = [state["dep_result"], state["secrets_result"], state["lint_result"]]
    
    # 2. Extract failures and completions
    failures = {r["node_id"]: r["error_detail"] for r in results if r["signal"] == Signal.FAILED}
    done_count = len([r for r in results if r["signal"] == Signal.DONE])
    
    # 3. Decision Logic
    if failures and done_count > 0:
        return AggregatorOutput(
            signal=Signal.PARTIAL,
            node_id="aggregator",
            orchestrator_summary=f"Phase completed with mixed results ({done_count}/{len(results)} passed).",
            result_uri=store(results),
            error_detail=ErrorDetail(
                failure_class=FailureClass.LOGIC_ERROR,
                message=f"{len(failures)} branch(es) failed."
            ),
            branch_breakdown=[...]  # Populate from branch results
        )
    elif failures:
        return AggregatorOutput(
            signal=Signal.FAILED,
            node_id="aggregator",
            orchestrator_summary="All branches failed.",
            error_detail=ErrorDetail(
                failure_class=FailureClass.LOGIC_ERROR,
                message="All parallel branches failed."
            ),
            branch_breakdown=[...]  # Populate from branch results
        )
    
    return AggregatorOutput(
        signal=Signal.DONE,
        node_id="aggregator",
        orchestrator_summary="All parallel checks passed successfully.",
        result_uri=store(results),
        branch_breakdown=[...]  # Populate from branch results
    )
```

**Rules:**
- The Orchestrator receives the aggregated abstraction.
- Use `PARTIAL` when some work was successful but remediation is needed for failures.
- The full branch history is always available in the `get_timeline()` / `audit_node()` logic.

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
            node_id="verify_python_output",
            orchestrator_summary=f"Verification failed. {test_results.failure_count} tests failed.",
            error_detail=ErrorDetail(
                failure_class=FailureClass.LOGIC_ERROR,
                message=f"{test_results.failure_count} tests failed.",
                expected="All tests passing",
                actual=f"{test_results.failure_count} failures"
            ),
            result_uri=store(test_results)
        )
    return ClawOutput(
        signal=Signal.DONE,
        node_id="verify_python_output",
        orchestrator_summary=f"All {test_results.total} tests passed.",
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
 
### 4.3 Stalemate Resolution (Deadlock Breaking)
If a node remains `STALLED` after its producer has completed (or if no producer exists), the Super-Orchestrator must intervene:
1.  **Identify the Gap**: Call `audit_node(stalled_id)` to see exactly what artifact is missing from the `requires` list.
2.  **Locate the Resource**: Search the `document_archive` (or external tools) for the missing URI.
3.  **Repair/Inject**: 
    - If the product exists under a different ID, update the stalled node's metadata.
    - If the product is missing, `register_node` for a new producer or manually inject the artifact URI.
4.  **Signal Resume**: The Orchestrator will automatically re-evaluate upon the next bag operation or a manual `poke` (empty update).

### 4.4 Node Design Principles

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

### 4.5 When to Use Each Signal (Super-Orchestrator Decision Tree)

When a node returns a signal, the Super-Orchestrator should respond as follows:

```
DONE              → Continue planning. Read summary. Update phase_history.
FAILED            → Read error_detail. Decide: fix the node, fix the input, or abort.
PARTIAL           → Read breakdown. Remediate failed branches or proceed if blockers are non-critical.
NEED_INFO         → Answer the clarification. Inject into state. Resume.
HOLD_FOR_HUMAN    → Thread suspends. Wait for `resume_job()` via external handler.
STALLED           → Analyze the "WAITING ON" hint. If the SO already possesses the 
                    data or can resolve the block via bag CRUD, it should "poke" the 
                    Orchestrator by injecting the missing resource or forcing a re-plan.
NEED_INTERVENTION → Treat as a bag-level problem. Call get_inventory(). 
                    Inspect state schema. Repair before resuming.
```

### 4.6 Registering a HITL Handler
The Super-Orchestrator or Developer must register a delivery mechanism for `HOLD_FOR_HUMAN` signals.

```python
def my_ui_handler(thread_id, human_request):
    # Send to Slack, WebSocket, or Email
    send_to_user_interface(thread_id, human_request)
bag.register_hitl_handler(my_ui_handler)
```

### 4.7 Cold-Start Sequence

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

### 4.8 Bag Repair (`NEED_INTERVENTION`)

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

## Part 8: The Document Manager & Precision Editor

In high-stakes workflows, agents frequently interact with large, persistent documents. The **Document Manager** pattern defines how agents perform CRUD operations on the `document_archive` while maintaining state precision and token efficiency.

### 8.1 Precision Updates (Line-Level Edits)

To avoid "Context Wash" (where a full rewrite accidentally omits or changes critical details), agents should perform **Precision Updates**. Instead of returning a full document, the agent returns a set of targeted edits.

**Pattern Rules:**
- **Never Rewrite by Default**: Full rewrites are reserved for the initial `CREATE` phase or a deliberate `REWRITE` signal.
- **Atomic Diffs**: Agents generate specific line-level or section-level changes (e.g., "Replace lines 120-145 with [New Content]").
- **State Concatenation**: The `DocumentArchive` manager (or a specialized node) applies these patches to the persistent artifact, keeping the history clear.

### 8.2 Specialized Editor Skills (Base Class Pattern)

Document handling logic can be complex. Rather than duplicating logic, use **Skill Inheritance**.

1.  **Base Skill (`base_editor.md`)**: Defines the core CRUD tools and precision-editing instructions (e.g., "How to generate a diff").
2.  **Specialized Skill (`reg_specialist.md`)**: Inherits the base editor logic and adds domain-specific constraints (e.g., "Ensure all edits comply with FDA 21 CFR Part 11").

**Example Node Decoration:**
```python
@clawnode(
    id="clinical_reg_editor",
    description="Precision editor for Clinical Regulatory documents.",
    # The agent inherits core editing intelligence + domain expertise
    skills=["base_editor.md", "clinical_reg_standards.md"],
    tools=["document_patcher", "regulatory_search"]
)
def edit_protocol(inputs: dict) -> ClawOutput:
    ...
```

### 8.3 Document Lifecycle Metrics

| Phase | Agent Action | Summary Goal |
| :--- | :--- | :--- |
| **CREATE** | Draft initial document. | "Created v1 of IB Justification." |
| **READ** | Scan for specific data. | "Found stability mismatch in Section 4.2." |
| **UPDATE** | Apply precision patches. | "Updated impurities table in Section 3 (Lines 45-60)." |
| **REWRITE** | Re-structure entire doc. | "Complete restructuring of CCDS for global alignment." |

---

## Appendix: Signal Quick Reference

```
DONE               ✅  Work complete. result_uri has the artifact.
FAILED             ❌  Unrecoverable failure. error_detail is required.
PARTIAL            📂  Phase complete with caveates. Breakdown in error_detail.
NEED_INFO          ❓  Needs upstream clarification. Super-Orchestrator answers.
HOLD_FOR_HUMAN     🧑  Human decision required. Orchestrator bypasses SO. Thread suspends.
STALLED            ⏳  Waiting on dependency resolution (Orchestrator-led).
NEED_INTERVENTION  🚨  Bag/state is broken. Super-Orchestrator repairs before resuming.
```