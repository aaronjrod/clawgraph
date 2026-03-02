# Phase 5: Production & Hardening

## Overview
Transition the project from a development prototype to a stable, production-ready system with durable state and specialized workflows.

## Goals
- Implement Sqlite/Postgres persistence for LangGraph.
- Build the "Persistent Heartbeat" deployment wrapper.
- Finalize HITL resumption logic aligned with lazy compilation.

## Detailed Tasks
1. **Durable Persistence**
    - [ ] Configure `SqliteSaver` (Dev) and `PostgresSaver` (Prod).
    - [ ] Validate checkpointing on `FAILED` or `SUSPENDED` states.
    - **Ref**: [05_ARCHITECTURE.md (Checkpointing)](file:///Users/aaronrodrigues/projects/clawgraph/notes/05_ARCHITECTURE.md#L167).

2. **Persistent Heartbeat Wrapper**
    - [ ] Implement the `while True` or Cron logic for recurring objectives.
    - [ ] Ensure `thread_id` continuity across heartbeats.
    - **Ref**: [06_patterns.md (Part 6.1)](file:///Users/aaronrodrigues/projects/clawgraph/notes/06_patterns.md#L336).

3. **HITL Resumption Refinery**
    - [ ] Optimize `resume_job()` to skip re-compilation unless manifest is dirty.
    - [ ] Test thread suspension and resumption with various human inputs.
    - **Ref**: [05_ARCHITECTURE.md (HITL Resumption)](file:///Users/aaronrodrigues/projects/clawgraph/notes/05_ARCHITECTURE.md#L177).

## Reminders
- [ ] **Orphaned Pointers**: Remind developers that archive artifacts persist even if a bag version is rolled back.
- [ ] **ACID**: Ensure state transitions are atomic to prevent bag corruption.
- **Source Ref**: [05_ARCHITECTURE.md (Durable Persistence)](file:///Users/aaronrodrigues/projects/clawgraph/notes/05_ARCHITECTURE.md#L160).
