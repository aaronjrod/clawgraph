# Appendix: Shelved Concerns & Future Considerations

This document serves as a repository for unresolved concerns, edge cases, and strategic gaps identified during the initial specification of ClawGraph. These items are shelved to maintain project momentum but must be addressed in future development cycles.

## 1. Edge Cases & Logical Ambiguities

### 1.1 `NEED_INFO` Escalation (target: USER)
- **Problem**: F-REQ-10 defines promotion to `NEED_INTERVENTION` upon budget exhaustion but does not distinguish between targets.
- **Concern**: If a `NEED_INFO` targeted at the `USER` (Human) times out, should it promote to `NEED_INTERVENTION` (Super-Orchestrator repair) or `HOLD_FOR_HUMAN` (Sync-point)? These have fundamentally different suspension and handling semantics.

### 1.2 `STALLED` State Transitions
- **Problem**: F-REQ-34 triggers prerequisite re-evaluation only after a `DONE` signal.
- **Concern**: If a producer node emits `FAILED`, dependent `STALLED` nodes are left in limbo. There is no specified transition (e.g., to `FAILED` or `NEED_INTERVENTION`) for nodes whose prerequisites can no longer be satisfied.

### 1.3 Precedence: `audit_hint` vs. `audit_policy`
- **Problem**: Both F-REQ-27 and Requirements §3.3 define audit triggers, but the conflict resolution is undefined.
- **Concern**: If a node returns `audit_hint: false` but the `audit_policy` mandates auditing (e.g., `always: true`), which signal takes precedence? An explicit hierarchy (e.g., Policy > Hint) is required.

### 1.4 `RESOLVING` Event Persistence
- **Problem**: §2.2.3 defines `RESOLVING` as a status event "NOT part of the node contract."
- **Concern**: It is ambiguous whether this event is persisted to the durable timeline (F-REQ-30/31) or exists only in-memory for the HUD/telemetry stream.

### 1.5 Rollback Scope
- **Problem**: `rollback_bag(version)` is marked as "Experimental" in the FRS but is a firm requirement in the Requirements Specification (§4.3).
- **Concern**: Need alignment on whether bag-level rollback is a v1 core feature or a deferred experimental capability.

## 2. Architectural & Strategic Gaps

### 2.1 TEE Compatibility (B-REQ-4)
- **Problem**: Mentioned as "Strategic" in the BRS but absent from FRS and Requirements.
- **Concern**: Lack of placeholder interfaces or constraints may lead to a design that accidentally precludes Trusted Execution Environment (TEE) integration in the future.

### 2.2 Cross-Bag Communication
- **Problem**: §6 of the Requirements doc recommends splitting bags for scale (>50 nodes) but provides no guidance on how these bags communicate or share state.
- **Concern**: Without a defined cross-bag interface, the "Bag of Nodes" model may become siloed, preventing the execution of complex, multi-domain workflows.

### 2.3 B-REQ-9 Traceability
- **Problem**: The "Discovery-First" requirement (B-REQ-9) has strong representation in Requirements §3.1 but is only addressed as a behavioral guideline in the FRS/Patterns doc.
- **Concern**: Traceability is fragile without a functional requirement (F-REQ) that mandates the discovery check.

## 3. Operational Risks

### 3.1 "Ghost Pointers" in Document Archive
- **Risk**: Deleting a node or rolling back a bag manifest does not delete the associated artifacts from the Document Archive.
- **Impact**: The Super-Orchestrator may inadvertently use outdated or "orphaned" URIs produced by nodes that no longer exist in the current bag version. A "Garbage Collection" skill/mechanism may be required.

### 3.2 Aggregator Complexity & Forgiveness
- **Risk**: The Aggregator's role as an abstraction layer (F-REQ-13) is non-trivial.
- **Impact**: If an Aggregator is too "forgiving" (converting critical failures into `PARTIAL` signals), it may lead the Orchestrator to continue a mission that should have been aborted or escalated, increasing token waste and risk.

### 3.3 Discovery-First Discipline
- **Risk**: Advisory guardrails (F-REQ-21) may be ignored by "eager" LLM models that skip inventory checks to save time/tokens.
- **Impact**: Redundant node registration and state drift.
- **Proposed Mitigation**: A "Discovery Gate" in the library that refuses `register_node` calls unless a recent inventory hash is provided.
