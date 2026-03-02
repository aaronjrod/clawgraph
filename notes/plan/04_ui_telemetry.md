# Phase 4: HUD & Telemetry (Observability)

## Overview
Implement the visualization layer that provides human operators and Super-Orchestrators with real-time insight into bag operations.

## Goals
- Implement `get_hud_snapshot()`.
- Build the "Implicit Linkage" scanner for data-flow visualization.

## Detailed Tasks
1. **HUD Snapshot API**
    - [ ] Create merged JSON output matching the schema in `patterns.md`.
    - [ ] Include node statuses (PENDING, RUNNING, DONE, FAILED).
    - **Ref**: [06_patterns.md (Part 7.1)](file:///Users/aaronrodrigues/projects/clawgraph/notes/06_patterns.md#L368).

2. **Implicit Linkage Engine**
    - [ ] Implement scanner that matches `result_uri` output of Node A to `inputs` of Node B.
    - [ ] Populate `links` array with `type: "data_flow"`.
    - **Ref**: [06_patterns.md (Part 7.2)](file:///Users/aaronrodrigues/projects/clawgraph/notes/06_patterns.md#L400).

3. **Mission Control Export**
    - [ ] Ensure snapshot is available via API for "Simple Graph Visualizer."
    - **Ref**: [03_FRS.md (F-REQ-23)](file:///Users/aaronrodrigues/projects/clawgraph/notes/03_FRS.md#L61).

## Reminders
- [ ] **Implicit Links**: Don't just rely on LangGraph edges; focus on the "URI handshake."
- [ ] **Real-Time**: SignalManager should update the HUD state immediately upon receiving a signal.
- **Source Ref**: [06_patterns.md (Mission Control)](file:///Users/aaronrodrigues/projects/clawgraph/notes/06_patterns.md#L364).
