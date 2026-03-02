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
    tags=["regulatory", "compliance"]
)
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

### 3. Tool Integration
Nodes can be assigned specific tools (Functions/CLI/API) that they are authorized to use.
- **`tools`**: A list of tool identifiers available to the agent.
- **Sandboxing**: Tools are executed in the node's local runtime context.

### 4. Signal-Based Output
Every node must return a `ClawOutput`, which dictates the flow of the entire Bag.
- **`signal`**: The tactical instruction (DONE, FAILED, NEED_INFO, etc.).
- **`summary`**: A context-lean summary for the Orchestrator.
- **`result_uri`**: A pointer to the raw, large-scale data (Tier 3).

## 🛰️ Lifecycle in the Workspace
- **Registration**: Architect calls `register_node` with the logic and metadata.
- **Discovery**: Orchestrator provides a "HUD Snapshot" of all registered agents.
- **Audit**: Architect can `audit_node` to view the full prompt construction and raw logs.
- **Reinforcement**: If a node fails, the Architect modifies the `skills.md` or the `system_prompt` and restarts the thread.

---
**Ref**: [06_patterns.md](file:///Users/aaronrodrigues/projects/clawgraph/notes/06_patterns.md), [05_ARCHITECTURE.md](file:///Users/aaronrodrigues/projects/clawgraph/notes/05_ARCHITECTURE.md)
