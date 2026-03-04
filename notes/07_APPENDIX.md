# Appendix: Shelved Concerns & Future Considerations

This document serves as a repository for unresolved concerns, edge cases, and strategic gaps identified during the initial specification of ClawGraph. These items are shelved to maintain project momentum but must be addressed in future development cycles.

## 1. Logical Ambiguities

### 1.1 `NEED_INFO` Escalation & Redundancy
- **Escalation Target**: F-REQ-10 defines promotion to `NEED_INTERVENTION` upon budget exhaustion but does not distinguish between targets. If `target: USER` (Human) times out, should it promote to `NEED_INTERVENTION` (Super-Orchestrator repair) or `HOLD_FOR_HUMAN` (Sync-point)?
- **Conceptual Redundancy**: If `NEED_INFO` can target a `USER`, the distinction between it and `HOLD_FOR_HUMAN` becomes blurred. Is `NEED_INFO` purely for programmatic clarification while `HOLD_FOR_HUMAN` is for existential approvals? This distinction is currently implicit and lacks formal specification.

### 1.2 `STALLED` State Transitions (Dead-End Identification)
- **Problem**: F-REQ-34 triggers prerequisite re-evaluation only after a `DONE` signal.
- **Concern**: If a producer node emits `FAILED`, dependent `STALLED` nodes whose prerequisites can no longer be satisfied are left in limbo. A transition path (e.g., to `FAILED` or `NEED_INTERVENTION`) for these "dead-end" nodes is missing.

### 1.3 Precedence: `audit_hint` vs. `audit_policy`
- **Conflict Resolution**: If a node returns `audit_hint: false` but the `audit_policy` mandates auditing (e.g., `always: true`), which signal takes precedence? An explicit hierarchy (e.g., Policy > Hint) is required to prevent Architect-Worker authority conflicts.

### 1.4 `RESOLVING` Event Persistence
- **Implementation Ambiguity**: §2.2.3 defines `RESOLVING` as a status event. It is unclear if this event is persisted to the durable timeline (F-REQ-30/31) or exists only in-memory for live HUD telemetry.

### 1.5 `partial_commit_policy` Default & Metadata
- **Defaults**: The FRS defines `eager` and `atomic` but specifies no default. Unpredictable library behavior is a risk if not explicitly set by the developer.
- **Artifact Validity**: In `eager` mode, artifacts stay committed even if the parent bubble ultimately emits `PARTIAL` or `FAILED`. Downstream consumer nodes currently have no standard way to know if a pick-up artifact came from an "incomplete" or "degraded" phase.

## 2. Architectural & Strategic Gaps

### 2.1 The "Simple" Orchestrator Scope Creep
- **Risk**: Requirements §2.2 labels the Orchestrator as "simple," yet the FRS assigns it high-level responsibilities: prerequisite resolution, escalation enforcement, exception interception, checkpointing for HITL, and commit policy management.
- **Impact**: This "simple" label undersells the implementation complexity, potentially misleading developers who attempt to replace the LLM-based Orchestrator with a non-LLM runtime.

### 2.2 `ClawOutput` Formal Specification
- **Gap**: While central to every signal and routing decision, the full `ClawOutput` schema lacks a canonical definition in the core spec suite.
- **Impact**: Relying on Pydantic mentions (F-REQ-14) or appendix quick-references creates implementation variance, especially for synthesized signals (F-REQ-11).

### 2.3 Governance Loop Termination Conditions
- **Gap**: F-REQ-23/B-REQ-10 define failure exits (max iterations) but omit the happy-path exit logic.
- **Impact**: It is unclear if the Super-Orchestrator can break early upon partial success, or how the system handles verification nodes that themselves fail (vs. the task failing).

### 2.4 Timeline Integrity & Volume
- **Integrity**: For a compliance-focused "System of Record" (B-REQ-16), the spec lacks requirements for immutability, signing, or tamper-evidence.
- **Volume**: At scale (large fan-outs + eager commits), the timeline may generate extreme event volume, creating potential DB bottlenecks and requiring retention/tiering policies not yet specified.

### 2.5 Cross-Bag Communication
- **Problem**: §6 of the Requirements doc recommends splitting bags for scale but provides no interface or guidance for state-sharing between bags.

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
