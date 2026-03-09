# Note 15: Test Gap Remediation Plan

Following the audit of the ClawGraph test suite against BRS/FRS/Architecture specifications, we are implementing a series of TDD tests to cover identified gaps. 

## Phase 1: Immediate TDD (Current Task)
We will implement baseline failing (or skeleton) tests for the following:

### 1. Max Iteration Limit (B-REQ-10)
- **Goal**: Ensure the Orchestrator respects `max_iterations` and escalates once reaching the limit.
- **File**: `tests/orchestrator/test_max_iterations.py`

### 2. HUD Snapshot Integrity (F-REQ-29)
- **Goal**: Verify `get_hud_snapshot()` returns the expected JSON structure merging manifest and signal states.
- **File**: `tests/orchestrator/test_hud_snapshot.py`

### 3. Selective Memory Pruning (F-REQ-16)
- **Goal**: Verify that once a node completes and produces a summary, the raw tool output is removed from the active `BagState` (preventing context bloat).
- **File**: `tests/orchestrator/test_pruning_verification.py`

### 4. Injection Testing (F-REQ-20)
- **Goal**: Create a test harness for triggering a node with adversarial/mocked inputs to simulate security stress-testing.
- **File**: `tests/orchestrator/test_injection.py`

## Phase 2: High-Complexity Logic (Follow-up)
These require more significant mock setup or architectural intervention:
- **Generate-Test-Reinforce Loop (B-REQ-5)**: Requires a multi-turn simulation where the SO fixes a node implementation and restarts.

-> This will be near-impossible based on how the SO works.

- **Temporal Navigation (B-REQ-17)**: Requires implementing/testing a "Seek" capability in the Timeline/Session DB.

- **SO Stalemate Intervention (B-REQ-15)**: Verify the SO can "force activate" a stalled node by manually resolving its prerequisites.

-> pushed both of above to v2