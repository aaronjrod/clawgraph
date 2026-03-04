# Appendix: Shelved Concerns & Future Considerations

This document serves as a repository for unresolved concerns, edge cases, and strategic gaps identified during the specification of ClawGraph. These items are shelved to maintain project momentum but must be addressed in future development cycles.

## 1. Logical Ambiguities

### 1.1 `NEED_INFO` Escalation & Redundancy
- **Escalation Target**: F-REQ-10 defines promotion to `NEED_INTERVENTION` upon budget exhaustion but does not distinguish between targets. If `target: USER` (Human) times out, should it promote to `NEED_INTERVENTION` (Super-Orchestrator repair) or `HOLD_FOR_HUMAN` (Sync-point)?
- **Conceptual Redundancy**: If `NEED_INFO` can target a `USER`, the distinction between it and `HOLD_FOR_HUMAN` becomes blurred. Is `NEED_INFO` purely for programmatic clarification while `HOLD_FOR_HUMAN` is for existential approvals? This distinction is currently implicit and lacks formal specification.

### 1.2 `STALLED` State Transitions (Dead-End Identification)
- **Problem**: F-REQ-34 triggers prerequisite re-evaluation only after a `DONE` signal.
- **Concern**: If a producer node emits `FAILED`, dependent `STALLED` nodes whose prerequisites can no longer be satisfied are left in limbo. A transition path (e.g., to `FAILED` or `NEED_INTERVENTION`) for these "dead-end" nodes is missing.

### 1.3 Precedence: `audit_hint` vs. `audit_policy`
- **Conflict Resolution**: If a node returns `audit_hint: False` but the `audit_policy` mandates auditing (e.g., `always: true`), which signal takes precedence?
- **Decision (from [12_clawoutput_spec.md](file:///Users/aaronrodrigues/projects/clawgraph/notes/12_clawoutput_spec.md))**: Policy > Hint (F-REQ-27). Needs enforcement logic in the Signal Manager or Orchestrator.

### 1.4 `RESOLVING` Event Persistence
- **Implementation Ambiguity**: §2.2.3 defines `RESOLVING` as a status event. It is unclear if this event is persisted to the durable timeline (F-REQ-30/31) or exists only in-memory for live HUD telemetry.

### 1.5 `partial_commit_policy` Default & Metadata
- **Defaults**: The FRS defines `eager` and `atomic` but specifies no default. Unpredictable library behavior is a risk if not explicitly set by the developer.
- **Artifact Validity**: In `eager` mode, artifacts stay committed even if the parent bubble ultimately emits `PARTIAL` or `FAILED`. Downstream consumer nodes currently have no standard way to know if a pick-up artifact came from an "incomplete" or "degraded" phase.

### 1.6 `PARTIAL` Signal Ambiguity Outside Aggregators
- **Problem**: F-REQ-6 allows any node to emit `PARTIAL`, but the patterns doc and all code examples exclusively model it as an Aggregator output with `branch_breakdown`.
- **Design Question**: Can a non-Aggregator leaf node emit `PARTIAL`? If so, what does `result_uri` point to? The `12_clawoutput_spec.md` validator requires `result_uri` on PARTIAL — but a single node with mixed results has no "branch breakdown."
- **Impact**: The semantics need to be either narrowed (Aggregator-only) or formalized for leaf nodes with a clear definition of what "partial" means for a single unit of work.

### 1.7 `NEED_INFO` Response Injection Path
- **Problem**: F-REQ-10 defines escalation for `NEED_INFO`, but the spec never specifies *how* the answer gets back to the node.
- **Gap**: `resume_job()` is defined for `HOLD_FOR_HUMAN` (F-REQ-26) with explicit checkpoint/rehydrate semantics, but `NEED_INFO` resolved by the SO has no equivalent API. Does the SO inject the answer into state and re-run the node? Does the Orchestrator do it? The `continuation_context` field in `12_clawoutput_spec.md` assumes this path exists but it's unspecified.

### 1.8 `max_iterations` Scope Ambiguity
- **Problem**: F-REQ-23 / B-REQ-10 define a max iteration limit but don't specify what counts as an "iteration."
- **Options**: One full Orchestrator reasoning turn? One node execution? One Generate-Test-Reinforce cycle? At the Orchestrator level, a single "iteration" might invoke multiple nodes — does each count, or only the outer loop?
- **Impact**: Inconsistent interpretation leads to either premature termination or runaway loops.

### 1.9 Prerequisite Re-evaluation After `PARTIAL`
- **Problem**: F-REQ-34 triggers STALLED re-evaluation only after `DONE`. But `12_clawoutput_spec.md` requires `result_uri` on `PARTIAL`, and under `eager` commit policy, PARTIAL branch artifacts *are* committed.
- **Gap**: PARTIAL artifacts may never unblock STALLED nodes even when those artifacts are valid, because the re-evaluation trigger only fires on `DONE`.
- **Proposed Fix**: Extend F-REQ-34 to trigger re-evaluation on both `DONE` and `PARTIAL` (with eager commits).

### 1.10 `HOLD_FOR_HUMAN` Duration & Timeout
- **Problem**: `NEED_INFO` has an `escalation_policy` with TTL and retry budget (F-REQ-10). `HOLD_FOR_HUMAN` has no equivalent.
- **Risk**: A thread can be suspended indefinitely. For long-running heartbeat deployments (patterns §6.1), abandoned `HOLD_FOR_HUMAN` threads may accumulate unbounded with no timeout, no escalation, and no garbage collection.

### 1.11 Implicit vs. Explicit Linking Inconsistency
- **Problem**: The HUD snapshot (patterns §7.2) distinguishes `topology` links (LangGraph edges) from `data_flow` links (URI dependencies). But in hub-and-spoke mode, topology links are just Orchestrator→Node — they convey zero information about actual execution order.
- **Gap**: The HUD's visual utility depends entirely on implicit link inference (Phase 4 work), but there is no spec for *how* URI matching works (exact match? prefix? glob?). The `links.py` module in the library structure has no corresponding specification.

---

## 2. Architectural & Strategic Gaps

### 2.1 The "Simple" Orchestrator Scope Creep
- **Risk**: Requirements §2.2 labels the Orchestrator as "simple," yet the FRS assigns it high-level responsibilities: prerequisite resolution, escalation enforcement, exception interception, checkpointing for HITL, and commit policy management.
- **Impact**: This "simple" label undersells the implementation complexity, potentially misleading developers who attempt to replace the LLM-based Orchestrator with a non-LLM runtime.

### 2.2 ~~`ClawOutput` Formal Specification~~ ✅ RESOLVED
- **Resolution**: The canonical `ClawOutput` Pydantic model is now fully specified in [12_clawoutput_spec.md](file:///Users/aaronrodrigues/projects/clawgraph/notes/12_clawoutput_spec.md), including two-layer schema (routing envelope + detail payload), sub-models (`ErrorDetail`, `InfoRequest`, `HumanRequest`, `BranchResult`), `AggregatorOutput` subclass, signal-conditional validators, versioning strategy, and the three-type distinction (ClawOutput vs Orchestrator status events vs Timeline events).

### 2.3 Governance Loop Termination Conditions
- **Gap**: F-REQ-23/B-REQ-10 define failure exits (max iterations) but omit the happy-path exit logic.
- **Impact**: It is unclear if the Super-Orchestrator can break early upon partial success, or how the system handles verification nodes that themselves fail (vs. the task failing).

### 2.4 Timeline Integrity & Volume
- **Integrity**: For a compliance-focused "System of Record" (B-REQ-16), the spec lacks requirements for immutability, signing, or tamper-evidence.
- **Volume**: At scale (large fan-outs + eager commits), the timeline may generate extreme event volume, creating potential DB bottlenecks and requiring retention/tiering policies not yet specified.

### 2.5 Cross-Bag Communication
- **Problem**: §6 of the Requirements doc recommends splitting bags for scale but provides no interface or guidance for state-sharing between bags.

### 2.6 Orchestrator Prompt Engineering Spec
- **Gap**: The Orchestrator is an LLM-based agent whose behavior is entirely defined by its system prompt. The spec suite provides no canonical prompt specification — only a note in plan Phase 2 to "draft a prompt that enforces signal-based routing."
- **Impact**: This is the single highest-risk implementation artifact. The Orchestrator's reasoning quality, signal routing, context discipline, and escalation behavior all depend on a prompt that currently has zero specification. Two different developers would produce fundamentally different Orchestrators.

### 2.7 Orchestrator Status Event Schema
- **Gap**: [12_clawoutput_spec.md](file:///Users/aaronrodrigues/projects/clawgraph/notes/12_clawoutput_spec.md) §8 identifies that Orchestrator status events (`STALLED`, `RUNNING`, `RESOLVING`) are a separate type from `ClawOutput`. But no formal schema exists for these events.
- **Impact**: The Signal Manager consumes these events and the HUD renders them, but their fields, persistence rules, and consumption logic are entirely unspecified. This is the remaining schema gap after `ClawOutput` was resolved.

### 2.8 Timeline Event Transformation Contract
- **Gap**: [12_clawoutput_spec.md](file:///Users/aaronrodrigues/projects/clawgraph/notes/12_clawoutput_spec.md) §8 identifies the Signal Manager's responsibility for transforming `ClawOutput` → Timeline Events. Neither the FRS nor the Architecture doc specifies this mapping.
- **Questions**: How does `orchestrator_summary` → `summary`? How does `completed_at - started_at` → `duration_ms`? Do detail payload fields go into `metadata`? What about Orchestrator status events — same pipeline or separate?
- **Risk**: Silent data loss or semantic drift during transformation.

### 2.9 Document Archive API & Semantics
- **Gap**: `document_archive` is referenced across the entire spec suite as the state key holding URI pointers. No document specifies its interface.
- **Open Questions**:
    - Operations: Get, Put, Delete, List, Tag?
    - Write access: Nodes directly? Only the Orchestrator? Only the BagManager?
    - Multi-domain tagging (F-REQ-17 / B-REQ-13): How does cross-bag visibility work?
    - Retention: What's the lifecycle of an archived artifact?
    - Key assignment: How does a node know what key to write its `result_uri` under?

### 2.10 `BagContract` Schema & Enforcement
- **Gap**: F-REQ-25 requires each bag to define a strict I/O schema. The library structure (`core/models.py`) implies this is a Pydantic model.
- **Open Questions**: What does the contract contain? Does it constrain the `document_archive` shape, the `ClawOutput` fields, or both? How is it validated — at registration time, at job start, or at runtime? What signal is emitted on violation (`SCHEMA_MISMATCH`)? Is the contract versioned alongside the manifest?

### 2.11 `rollback_bag` Semantics
- **Gap**: The API (FRS §3.2) lists `rollback_bag(version)` as "experimental" and the appendix flags the ghost pointer problem (§3.1). The remaining unknowns:
    - Does rollback affect currently running jobs?
    - Does it invalidate existing checkpoints?
    - Can you roll *forward* (replay)?
    - Does the timeline record the rollback event itself (for audit)?
- **Decision Required**: Defer entirely to v2, or define minimal semantics for v1.

### 2.12 Multi-Bag Orchestration
- **Gap**: The BRS and requirements doc both recommend splitting bags at scale. The CTO use case (`11_use_case_cto.md`) shows three separate bags with dotted-line relationships. But there is zero specification for how a Super-Orchestrator runs a job *across* multiple bags.
- **Open Questions**: Does it call `start_job()` on each independently? How do bags share artifacts? Is there a cross-bag `document_archive` or does the SO manually copy URIs? The dotted lines in the CTO diagram imply a relationship with no interface behind them.

### 2.13 Node Identity & Lifecycle
- **Gap**: `node_id` is required on `ClawOutput` and used as the primary key across the manifest, Signal Manager, and timeline. But the spec doesn't define:
    - Scope: Globally unique or bag-scoped?
    - Persistence: Does `update_node` preserve the ID? Does it get a version suffix?
    - Collision: Can two bags have nodes with the same ID?
    - Ghost identity: If a node is deleted and re-registered with the same ID, is it the "same" node for timeline/audit purposes?

---

## 3. Operational Risks

### 3.1 "Ghost Pointers" & Rollback Paradox
- **Risk**: Rollbacks (`rollback_bag`) combined with `eager` commits create a temporal paradox. Artifacts from a rolled-back version (N-1) remain in the archive, potentially being used by the current version (N-2) without context or a valid "producer" node in the current manifest.
- **Mitigation**: A "Garbage Collection" skill or enhanced metadata tagging for artifacts may be required.

### 3.2 Aggregator Single Point of Failure (SPOF)
- **Risk**: If an Aggregator node crashes, F-REQ-11 synthesizes a `SYSTEM_CRASH`, potentially losing the entire branch-level context the Aggregator had collected.
- **Mitigation**: Aggregators may warrant specialized crash-recovery or context-persisting patterns.

### 3.3 Discovery Enforcement (The "Discovery Gate")
- **Risk**: Advisory guardrails for the "Discovery-First" discipline (B-REQ-9) are likely to be ignored by "eager" LLM models to save tokens.
- **Proposed Mitigation**: Promote the "Discovery Gate" to a v1 functional requirement, refusing `register_node` calls unless a recent inventory hash is provided.

### 3.4 Bag Contract Validation Timing
- **Risk**: The spec defines per-bag contracts (F-REQ-25) but doesn't specify *when* validation occurs.
- **Impact**: If validation only occurs at runtime, "state drift" and incompatible node integrations may pass the registration phase, only to crash the critical path mid-job.

### 3.5 Heartbeat State Accumulation
- **Risk**: The Persistent Heartbeat pattern (patterns §6.1) reuses the same `thread_id` across invocations. Over time, the LangGraph checkpoint grows unbounded.
- **Impact**: The spec mentions no state pruning, compaction, or archival strategy for long-lived threads. A CTO bag running hourly heartbeats for months would see pathological checkpoint size and resume cost.
- **Mitigation**: Periodic thread rotation, checkpoint compaction, or a "summarize and reset" pattern.

### 3.6 Signal Manager Crash Recovery
- **Risk**: Architecture §3 states the Signal Manager is "transient" and resets on crash. But §10.6 describes it as the Event Emitter to the Session DB.
- **Gap**: If the Signal Manager crashes mid-emission, some timeline events may be lost or partially written. The spec provides no crash-recovery, write-ahead logging, or at-least-once delivery guarantee.
- **Impact**: The "System of Record" (B-REQ-16) has a silent durability gap.

### 3.7 Concurrent Job Isolation
- **Risk**: The `start_job` API doesn't address whether multiple jobs can run simultaneously on the same bag.
- **Impact**: If two jobs share the same `document_archive`, they may clobber each other's artifacts. If they share the Signal Manager, status events will interleave. The HUD snapshot would show conflated state.
- **Assumption**: The spec implies single-job-per-bag but never states it explicitly. This needs to be either enforced (reject concurrent `start_job`) or specified (isolation semantics).

### 3.8 LLM Provider Failure Handling
- **Risk**: Each node can specify a `provider` and `model` (ClawNode spec §2). If the provider API is down or rate-limited, exception interception (F-REQ-11) synthesizes a `SYSTEM_CRASH`.
- **Problem**: `SYSTEM_CRASH` implies a node bug. A transient provider outage is qualitatively different — it's retriable and not the node's fault. The current taxonomy conflates these.
- **Gap**: No retry-at-provider-level strategy, no fallback model config, and no clear `failure_class` for LLM API errors (closest is `TOOL_FAILURE`, but the LLM call isn't a "tool" in the spec's vocabulary).

### 3.9 Skill File Versioning & Drift
- **Risk**: Nodes reference `.md` skill files injected into system prompts at runtime (ClawNode spec §3). Skills are files on disk that can be edited between invocations, between heartbeats, or even during a job (since `update_node` can modify skills).
- **Audit Gap**: The spec has no mechanism to snapshot which skill version was active when a node ran. Timeline events record the `node_id` and `signal`, but not the prompt or skill content that produced it.
- **Impact**: For compliance-grade auditing (B-REQ-16), the system cannot prove what instructions a node was following at execution time.

### 3.10 `GuardNode` Specification Gap
- **Risk**: The security architecture (Architecture §7) references a `GuardNode` pattern that intercepts dangerous tool calls. No spec defines its implementation.
- **Open Questions**: Is it a decorator, a wrapper, or a separate node in the graph? How are "dangerous" tools identified? Where are policies stored? How does it interact with `HOLD_FOR_HUMAN`?
- **Impact**: The architecture diagram shows it as a first-class component, but it has no FRS requirement, no patterns doc entry, and no plan phase task. It's effectively an unreferenced design artifact.

---

## 4. Design Debt from `ClawOutput` Spec

Items introduced by the [12_clawoutput_spec.md](file:///Users/aaronrodrigues/projects/clawgraph/notes/12_clawoutput_spec.md) that require follow-up specification.

### 4.1 `continuation_context` Serialization & Size
- **Risk**: `continuation_context` is typed as `dict | None` with no constraints. It's persisted through LangGraph checkpointing (serialized to Session DB).
- **Gap**: No size limit, no schema constraint, no serialization format requirement. A node that dumps its entire internal state could bloat checkpoints and violate the pointer-based-state philosophy.
- **Mitigation**: Consider a max byte limit or require that `continuation_context` contain only serializable primitives and URI pointers.

### 4.2 `output_id` Deduplication Mechanics
- **Gap**: [12_clawoutput_spec.md](file:///Users/aaronrodrigues/projects/clawgraph/notes/12_clawoutput_spec.md) §5.3 states the Orchestrator and Signal Manager should deduplicate on `output_id`. Neither component's spec defines *how*.
- **Open Questions**: Does the Signal Manager keep an in-memory set? Does the Session DB enforce a unique constraint? What's the retention window for dedup — current job, current thread, or forever?

### 4.3 `schema_version` Migration Functions
- **Gap**: The versioning strategy (§7) references "a registered migration function" for backward compatibility. The registration mechanism, location (per-bag or global), and function signature are unspecified.
- **Severity**: Low for v1 (only one version exists). Becomes critical before v2 ships.

