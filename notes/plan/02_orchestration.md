# Phase 2: Tactical Hub (The Orchestrator)

## Overview
Implement the centralized "Runtime" layer that uses LangGraph to route signals between the Super-Orchestrator and the Bag of Nodes.

## Goals
- Implement the LangGraph "Hub-and-Spoke" topology.
- Build the "Lazy Compilation" engine.
- Define the Orchestrator's system prompt (The "Tactical Director").

## Detailed Tasks
1. **LangGraph Topology**
    - [ ] Define the central `Orchestrator` node in LangGraph.
    - [ ] Implement conditional edges based on `ClawOutput.signal`.
    - **Ref**: [05_ARCHITECTURE.md (Topology)](file:///Users/aaronrodrigues/projects/clawgraph/notes/05_ARCHITECTURE.md#L50).

2. **Lazy Compilation Engine**
    - [ ] Implement `compile_graph_if_dirty()` logic.
    - [ ] Check `manifest_version` against `last_compiled_version`.
    - **Ref**: [05_ARCHITECTURE.md (Scale Constraints)](file:///Users/aaronrodrigues/projects/clawgraph/notes/05_ARCHITECTURE.md#L202).

3. **Orchestrator System Prompt**
    - [ ] Draft a prompt that enforces signal-based routing and context discipline.
    - [ ] Ensure it only interacts with Tier 1 metadata and phase summaries.
    - **Ref**: [06_patterns.md (Part 5)](file:///Users/aaronrodrigues/projects/clawgraph/notes/06_patterns.md#L318).

## Reminders
- [ ] **No Raw Access**: The Orchestrator MUST NEVER see raw node outputs (Tier 3).
- [ ] **Aggregation**: Subgraphs must use the Aggregator pattern defined in patterns.md.
- **Source Ref**: [05_ARCHITECTURE.md (Orchestrator Logic)](file:///Users/aaronrodrigues/projects/clawgraph/notes/05_ARCHITECTURE.md#L100).
