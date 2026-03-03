# Business Requirement Specifications (BRS): ClawGraph

## 1. Executive Summary
The primary business objective of ClawGraph is to reduce the operational cost and security risks associated with autonomous LLM agents while increasing their reliability and developer productivity. By providing a structured yet flexible orchestration layer, ClawGraph enables organizations to deploy "agentic teams" that can solve complex, multi-step problems without the "token burn" typical of existing autonomous systems.

### 1.1 The Core Narrative: From Cold-Start to Calibration
ClawGraph is designed around a "blank slate" user story:
1.  **Cold-Start**: A high-level agent (Super-Orchestrator) is initialized in a sovereign workspace with only the ClawGraph library and a goal.
2.  **Capability Bootstrapping**: The lead agent designs and registers a specialized "Bag of Nodes" (the teammates) tailored to the task.
3.  **Governance & Execution**: The Orchestrator manages the task execution, surfacing signals and summaries to the lead agent who audits, repairs, and calibrates the workspace as needed.

## 2. Business Objectives
- **Cost Reduction**: Minimize unnecessary token consumption by implementing hierarchical summarization and efficient context management.
- **Risk Mitigation**: Provide verifiable security guiderails and human-in-the-loop (HITL) checkpoints to prevent unauthorized system actions (RCE, data exfiltration).
- **Productivity Gains**: Enable "tactical agentic coding" where teams of specialized agents work in parallel, overseen by a high-level lead agent.
- **Observability**: Deliver a "Mission Control" level of visibility into agent reasoning, signals, and task status.

## 3. Target Audience
- **Developers**: Building complex autonomous workflows and digital operators.
- **Enterprise Security Teams**: Requiring audit trails and enforceable guardrails for AI agents.
- **Product Managers**: Looking for reliable, predictable AI-driven automation tools.

## 4. Key Business Requirements

### 4.1 Cost & Efficiency (Token Management)
- **B-REQ-1**: The system must provide a mechanism to integrate summaries into node outputs to prevent unnecessary LLM calls and context growth.
- **B-REQ-2**: The system must support "Phase-Based" execution where only the final outcome of a sub-task is kept in the primary orchestrator's memory.

### 4.2 Security & Compliance (Safety)
- **B-REQ-3**: The system must allow for mandatory human or policy-driven approvals before executing high-risk commands (e.g., shell execution, file deletion).
- **B-REQ-4**: (Strategic) The system should be compatible with Trusted Execution Environments (TEEs) for cryptographic proof of safety compliance.

### 4.3 Reliability & Repeatability
- **B-REQ-5**: The system must support "Generate-Test-Reinforce" loops where failed workflows are automatically analyzed and corrected by a Super-Orchestrator.
- **B-REQ-6**: Workflows must be representable as repeatable, versioned templates (the "Bag of Nodes").
- **B-REQ-9 (Preventing 'Leaps')**: The system must enforce a "Discovery-First" approach where the Super-Orchestrator is grounded in existing bag capabilities (node summaries) before proposing new nodes or workflows, preventing redundant or conflicting implementations.
- **B-REQ-10 (Loop Governance)**: The system shall support a configurable "Max Iteration" limit for the Generate-Test-Reinforce loop to prevent runaway token expenditure.
- **B-REQ-11 (Production Persistence)**: The system shall support database-backed session storage to ensure ACID compliance and facilitate long-term analytics of agent performance.

### 4.4 User Experience & Trust
- **B-REQ-7**: Provide a real-time visualization of the agent collective's status to build user trust and facilitate manual intervention.
- **B-REQ-8**: Enable a "Lead-Teammate" interaction model where users (or lead agents) can provide feedback on artifacts (plans, diffs) asynchronously.

### 4.5 Orchestration Intelligence (HUD-Driven)
- **B-REQ-12 (Structured Failure Metadata)**: Nodes signaling `FAILED` must provide a structured analysis object (e.g., expected thresholds vs. actual outcomes) to allow the Super-Orchestrator to perform automated root-cause analysis.
- **B-REQ-13 (Multi-Domain Document Tagging)**: The Document Archive must support multi-bag tagging to allow artifacts to be visible across sovereign workspaces while maintaining a strict "owner" domain and preventing unauthorized cross-talk.
- **B-REQ-14 (Sovereign Dependency Resolution)**: The Orchestrator shall be responsible for resolving input prerequisites across bags. If a node declares a required artifact (prerequisite) that is not yet present in the Document Archive, the Orchestrator shall mark the node as `STALLED` at scheduling time and prioritize the activation of the producer node.
- **B-REQ-15 (Super-Orchestrator Stalemate Intervention)**: The Super-Orchestrator (Architect) shall monitor STALLED states. If the SO identifies that a block is solvable via a hidden dependency (manual injection or bag repair), it must have the capability to "prime" the state or force activation to resolve the stalemate.

### 4.6 Temporal Transparency & Accountability
- **B-REQ-16 (Timeline as First-Class Artifact)**: The system must maintain a durable, chronological event log of all lifecycle transitions. This serves as the "System of Record" for post-mortem analysis, billing transparency, and compliance auditing.
- **B-REQ-17 (Accountability UX)**: The visualization layer must support "Temporal Navigation" (replay/seek) to build user trust by allowing operators to inspect exactly how a conclusion was reached over time.
- **B-REQ-18 (Contextual Intervention)**: Human-in-the-loop requests must be surfaced with their preceding execution context (the "lead-up" events) to ensure reviewers have sufficient grounding for their decisions.

## 5. Success Metrics & Traceability
- **Token Efficiency**: 30%+ reduction in average tokens per successful multi-step task compared to uncoordinated autonomous sessions.
    - *Driven by*: Pointer-Based State, Integrated Summaries, and Selective Memory Pruning.
- **Correctness**: Higher rate of "first-time-right" completions for complex tasks via the reinforcement loop.
    - *Driven by*: Generate-Test-Reinforce cycle, Discovery-First Grounding, and `audit_policy` oversight.
- **Intervention Speed**: Reduced time for a human operator to identify and fix a stalled agentic loop.
    - *Driven by*: Signal Manager HUD and explicit `NEED_INFO`, `HOLD_FOR_HUMAN`, and `NEED_INTERVENTION` signals.
