# ClawNode Specification (Refined)

The `ClawNode` is the atomic unit of the Sovereign Workspace. It is an **Agent** managed by the Architect (Super-Orchestrator) and coordinated by the Tactical Director (Orchestrator).

## 🛠️ Definition & Metadata

A node is defined using the `@clawnode` decorator, which registers it into a specific `ClawBag` via the `bag` parameter.

```python
@clawnode(
    id="regulatory_specialist",
    bag="clinical_trial_ops",     # CRITICAL: Maps the node to a specific Sovereign Workspace
    description="Analyzes clinical trial data against FDA/EMA standards.",
    provider="anthropic",        # Optional: default set at Bag level
    model="claude-3-5-sonnet",   # Optional: default set at Bag level
    skills=["fda_compliance.md", "protocol_benchmarking.md"],
    tags=["regulatory", "compliance"],
    requires=["clinical_data_source"]   # OPTIONAL: Explicit artifact dependencies
)
```

### 0.1 Metadata Attributes
| Field | Type | Description |
| :--- | :--- | :--- |
| **`id`** | `str` | Unique identifier for the node within the bag. |
| **`description`** | `str` | High-level persona/capability summary for the Orchestrator. |
| **`bag`** | `str` | The name of the Sovereign Workspace this node belongs to. |
| **`skills`** | `list[str]` | List of `.md` skill files to inject into the system prompt. |
| **`requires`** | `list[str]` | **Prerequisite IDs** from the `document_archive` required before this node can fire. |
| **`escalation_policy`** | `dict` | (Optional) `{ttl_seconds: int, max_retries: int}`. Overrides bag-level defaults. |
def analyze_compliance(inputs: dict) -> ClawOutput:
    ...
```

## 🧠 Node Architecture (Agentic)

### 1. Bag Association (`bag`)
Nodes are no longer "orphans." They must be associated with a named `ClawBag` during decoration. This allows the Super-Orchestrator to manage multiple workflows (e.g., `clinical_ops`, `marketing_launch`, `regulatory_filing`) within the same repository without cross-talk.

### 2. Provider & Model Selection
Nodes are no longer "one model fits all." The Architect can specify:
- **`provider`**: (e.g., `openai`, `anthropic`, `google`, `ollama`)
- **`model`**: Specific model identifier (e.g., `gpt-4o`, `gemini-1.5-pro`).
- **Rationale**: Optimization for cost vs. reasoning depth (e.g., use a "flash" model for PII scanning, a "pro" model for protocol benchmarking).

### 3. Context Injection (Skills & Summaries)
When a node is invoked, the runtime constructs its system prompt from several sources:
- **`skills/*.md`**: The runtime reads referenced skill files and appends them to the context.
- **Architect-Defined Summary**: A high-level description of what this node's persona should be.
- **Dynamic Context**: The Architect can inject specific "Instructions of hte Day" or "Generation-time Info" into the system prompt during an `update_node` operation.
- **Bag Inventory**: A list of *other* nodes in the bag (Tier 1 metadata only) so the agent knows who it can delegate to (via signals).

### 3.1 Skill Composition (Inheritance)
To implement "Base Class" behaviors (e.g., a generic `DocumentManager`), the Architect can compose skills. The runtime processes the `skills` list sequentially, allowing a `base_editor.md` to be specialized by `clinical_standards.md`. This reinforces the Sovereign Workspace by keeping domain-agnostic logic reusable.

### 4. Tool Integration (Capabilities)
Nodes are authorized to use specific **Tools**.
- **`tools`**: A list of tool identifiers (e.g., `["internet_search", "email_client"]`).
- **Execution**: Tools are deterministic capabilities (APIs/CLI) that the agent calls.
- **Rules**: Every tool call is intercepted by a `GuardNode` (see ARCHITECTURE.md).

### 5. Skills vs. Tools (The Mental Model)
| Component | What it is | Role |
| :--- | :--- | :--- |
| **Skill** | `.md` file | **Instructional Context**. Provides "how-to" and domain expertise. |
| **Tool** | Function/API | **Capability**. The actual "hands" of the agent to perform actions. |

**Example**: A Regulatory Agent has the **Skill** of knowing *how* to vet a document, but uses the **Tool** `pdf_parser` to actually read it.

### 4. Signal-Based Output (`ClawOutput`)
Every node must return a `ClawOutput`, which dictates the flow of the entire Bag.

> **Canonical Definition**: [12_clawoutput_spec.md](file:///Users/aaronrodrigues/projects/clawgraph/notes/12_clawoutput_spec.md)
>
> The full Pydantic model with all fields, validators, and sub-models is defined in the canonical spec. Key fields for node authors:

| Field | Type | Description |
| :--- | :--- | :--- |
| **`signal`** | `Signal` | `DONE`, `FAILED`, `PARTIAL`, `NEED_INFO`, `HOLD_FOR_HUMAN`, `NEED_INTERVENTION`. |
| **`node_id`** | `str` | Unique identifier for this node. |
| **`orchestrator_summary`** | `str` | Terse, routing-relevant explanation (1-2 sentences). |
| **`operator_summary`** | `str \| None` | Human-readable summary for HUD. Falls back to `orchestrator_summary` if None. |
| **`result_uri`** | `str \| None` | Pointer to Tier 3 results. **Required** for `DONE` and `PARTIAL`. |
| **`error_detail`** | `ErrorDetail \| None` | **Required** on `FAILED`, `PARTIAL` (with failures), `NEED_INTERVENTION`. Structured Pydantic model with `failure_class`. |
| **`info_request`** | `InfoRequest \| None` | **Required** on `NEED_INFO`. Includes `question`, `context`, `target`. |
| **`human_request`** | `HumanRequest \| None` | **Required** on `HOLD_FOR_HUMAN`. Self-contained message for the human. |
| **`audit_hint`** | `bool \| None` | `True` = self-flag for audit. `None` = no preference. `False` = opted out. |
| **`continuation_context`** | `dict \| None` | Opaque state for suspended node resumption on `NEED_INFO`/`HOLD_FOR_HUMAN`. |

#### Sovereign Delegation via SO-Skill Context

> [!TIP]
> **`next_steps_hint`** is NOT a field on `ClawOutput`. It is a **SO-skill-level convention**: when a node wants to recommend a tactical path, it does so via its `orchestrator_summary` (e.g., "CMC validation is likely next") or through the Architect's skill instructions. This preserves the decoupling between bags — a Regulatory specialist doesn't need to know the internal structure of the CMC bag.

## 🛰️ Lifecycle in the Workspace
- **Registration**: Architect calls `register_node` with the logic and metadata.
- **Discovery**: Orchestrator provides a "HUD Snapshot" of all registered agents.
- **Audit**: Architect can `audit_node` to view the full prompt construction and raw logs.
- **Reinforcement**: If a node fails, the Architect modifies the `skills.md` or the `system_prompt` and restarts the thread.

---
**Ref**: [06_patterns.md](file:///Users/aaronrodrigues/projects/clawgraph/notes/06_patterns.md), [05_ARCHITECTURE.md](file:///Users/aaronrodrigues/projects/clawgraph/notes/05_ARCHITECTURE.md)
