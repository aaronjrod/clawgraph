# Note 16: Orchestrator Stability & Loop Prevention

**Date**: 2026-03-12
**Status**: Implemented

## Problem Statement
During complex multi-turn interactions (specifically Human-In-The-Loop resumptions), the Orchestrator exhibited two critical failure modes:
1. **Context Gap**: Leaf nodes (Tier 2) were not receiving the `human_response` injected into the BagState, causing them to re-request the same data indefinitely.
2. **Dispatch Looping**: The Orchestrator LLM would occasionally "stubbornly" re-dispatch a node that had just signaled `HOLD_FOR_HUMAN`, ignoring the hold and exhausting its iteration budget (10/10).
3. **Chat Termination**: Posting a chat message via `post_chat_message` triggered a premature escalation because the hub routing logic only handled `DONE` and `HOLD_FOR_HUMAN` as terminal, and everything else was treated as an error.

## Technical Resolution

### 1. Leaf Node Context Injection (F-REQ-MOD-01)
The `run_cto_llm_node` utility in `llm_utils.py` now explicitly checks for `human_response` in the state and prepends it to the `user_content` provided to the node's LLM call.

### 2. Orchestrator Sanity Guard (F-REQ-MOD-02)
Added a hard-coded "Sanity Guard" in `llm_node.py`. If the orchestrator attempts to dispatch the *same* node that previously requested a human hold, and no new human input has been processed in that turn, the system interposes and forces a `suspend()` call. This prevents budget-wasting loops caused by LLM hallucinations.

### 3. Hub Continuity Fix (F-REQ-MOD-03)
Modified `hub.py` to allow the orchestrator to continue its reasoning loop (returning `ROUTE_NEXT_NODE`) if the signal is `None`. This supports multi-turn orchestration where the agent may chat or update metadata before dispatching.

## Verification
- Validated via `nda_admin_packager` test case: Orchestrator now correctly chats with examples and then suspends, instead of looping to 10 iterations.
