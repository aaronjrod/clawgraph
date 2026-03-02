# Phase 3: The Architect's Tools (Super-Orchestrator Skills)

## Overview
Empower the "Lead Teammate" (Super-Orchestrator) with the tools required to build, edit, and audit the bag.

## Goals
- Implement the Node CRUD API (register/update/delete).
- Codify the "Discovery-First" protocol.
- Implement the `audit_node()` function for Tier 2/3 access.

## Detailed Tasks
1. **Node CRUD API**
    - [ ] `register_node(code, metadata)`: Stores Tier 2 code and Tier 1 metadata.
    - [ ] `update_node(id, code, metadata)`: Updates existing records and increments manifest version.
    - **Ref**: [03_FRS.md (API Definitions)](file:///Users/aaronrodrigues/projects/clawgraph/notes/03_FRS.md#L68).

2. **Discovery-First Enforcement**
    - [ ] Implement `get_inventory()` return shape.
    - [ ] Add advisory warnings if CRUD is called before inventory retrieval.
    - **Ref**: [06_patterns.md (Part 4.1)](file:///Users/aaronrodrigues/projects/clawgraph/notes/06_patterns.md#L214).

3. **Audit Mechanism**
    - [ ] `audit_node(id)`: Returns full source (Tier 2) and result archive (Tier 3).
    - [ ] Implement `audit_policy` check logic.
    - **Ref**: [05_ARCHITECTURE.md (Audit Triggers)](file:///Users/aaronrodrigues/projects/clawgraph/notes/05_ARCHITECTURE.md#L225).

## Reminders
- [ ] **Security**: Tier 2/3 access must be restricted to the Super-Orchestrator.
- [ ] **Scale**: Reminder to Super-Orchestrator to split bags at ~50 nodes.
- **Source Ref**: [06_patterns.md (Super-Orchestrator Skills)](file:///Users/aaronrodrigues/projects/clawgraph/notes/06_patterns.md#L210).
