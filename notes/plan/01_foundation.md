# Phase 1: Foundation & State (The Bag)

## Overview
Establish the core data structures, signaling enum, and state management logic that form the "Library" layer of the Sovereign Workspace.

## Goals
- Define immutable `Signal` enums and the base `ClawOutput` Pydantic model.
- Implement the `SignalManager` for internal state transitions.
- Build the `BagManager` to handle node registration and manifest versioning.

## Detailed Tasks
1. **Core Schemas**
    - [ ] Define `Signal` Enum (DONE, FAILED, PARTIAL, NEED_INFO, HOLD_FOR_HUMAN, NEED_INTERVENTION).
    - [ ] Define `FailureClass` Enum (LOGIC_ERROR, SCHEMA_MISMATCH, TOOL_FAILURE, GUARDRAIL_VIOLATION, SYSTEM_CRASH).
    - [ ] Create `ClawOutput` Pydantic model per canonical spec: [12_clawoutput_spec.md](file:///Users/aaronrodrigues/projects/clawgraph/notes/12_clawoutput_spec.md).
    - [ ] Create sub-models: `ErrorDetail`, `InfoRequest`, `HumanRequest`, `BranchResult`.
    - [ ] Create `AggregatorOutput(ClawOutput)` subclass.
    - [ ] **[NEW]** Define `ClawNodeMetadata` schema (`provider`, `model`, `skills`, `tools`).
    - **Ref**: [12_clawoutput_spec.md](file:///Users/aaronrodrigues/projects/clawgraph/notes/12_clawoutput_spec.md), [10_clawnode_spec.md](file:///Users/aaronrodrigues/projects/clawgraph/notes/10_clawnode_spec.md).

2. **The Signal Manager**
    - [ ] Implement `SignalManager.process_signal()` logic.
    - [ ] Ensure `NEED_INTERVENTION` is triggered on schema drift.
    - **Ref**: [05_ARCHITECTURE.md (Signal Manager)](file:///Users/aaronrodrigues/projects/clawgraph/notes/05_ARCHITECTURE.md#L120).

3. **Bag Manager & Manifest**
    - [ ] Implement `register_node` (local storage/manifest update).
    - [ ] Implement versioning logic for the `BagManifest`.
    - [ ] Create `get_inventory()` tool for full manifest retrieval.
    - **Ref**: [03_FRS.md (F-REQ-15)](file:///Users/aaronrodrigues/projects/clawgraph/notes/03_FRS.md#L34).

## Reminders
- [ ] **Context-Lean**: Ensure `BagManifest` only stores descriptions and Tier 1 metadata, not full code (Tier 2).
- [ ] **Immutability**: Once a job starts, the manifest version must be locked.
- **Source Ref**: [05_ARCHITECTURE.md (Sovereign Workspace)](file:///Users/aaronrodrigues/projects/clawgraph/notes/05_ARCHITECTURE.md#L15).
