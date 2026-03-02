# ClawGraph 👜
### Hierarchical Agent Orchestration for High-Stakes Workflows

**ClawGraph** is a framework built on [LangGraph](https://github.com/langchain-ai/langgraph) designed to handle the "Complexity Wall" in AI agent systems. It introduces a modular **Sovereign Workspace** model that separates high-level architectural planning from tactical execution.

---

## 🛑 The Problem: The "Complexity Wall"
Most agentic systems fail as they scale. When a single agent or a simple chain tries to handle 50+ tools, complex reasoning, and long-running state, you encounter:
- **Context Saturation**: The agent gets "lost" in its own history.
- **Reasoning Drift**: Subtle hallucinations or incorrect tool calls compound over time.
- **Troubleshooting Debt**: > [!IMPORTANT]
> Manually-built multi-agent systems (MAS) are notoriously brittle. They take weeks to define, and even longer to troubleshoot and capture the long tail of edge cases. **ClawGraph lets the AI handle this debt for you.**

## ✅ The Solution: The Sovereign Workspace
ClawGraph solves this by shifting the burden of system maintenance from the human to the AI. Instead of you manually wiring every edge, you provide the goal to the **Architect**, who then manages the troubleshooting, testing, and reinforcement of the agent bag for you.

We partition labor into three distinct tiers:

1.  **The Architect (Super-Orchestrator)**: An intelligent agent (e.g., **OpenClaw**, **Claude Code**, **Codex**, or **Antigravity**) that builds, audits, and repairs the system. It writes the node code and debugs the graph.
2.  **The Tactical Director (Orchestrator)**: A specialized runtime that doesn't "do" the work, but routes results between nodes based on standardized signals.
3.  **The Library (Bag of Agents)**: A dynamic collection of atomic, task-specific **Agent Nodes**. The Orchestrator only sees metadata (summaries); the Architect manages the underlying agent logic.

---

## 🎯 Who is this for?
- **AI Engineers** building complex autonomous systems that require more than just a simple RAG chain.
- **DevOps Teams** automating multi-stage security, linting, and deployment pipelines.
- **Data Analysts** building agents that need to perform long-running, auditable research and synthesis.

## 🌟 What it enables
- **Massive Scale**: Orchestrate 50+ specialized nodes in a single workflow without context window saturation.
- **Deep Auditability**: Every node transition is logged via pointers. Audit logic only when things look "wrong."
- **Self-Healing & Evolution**: The Super-Orchestrator can detect failures and "hot-fix" the bag by registering or updating nodes in real-time. This enables **Coding Agents to build, test, and reinforce their own workflows** autonomously.
- **Human-in-the-Loop**: Native suspension and resumption for sensitive decisions.

## 🚀 Use Cases
- **Autonomous Software Engineering**: One node scans for secrets, another runs tests, a third refactors code—all coordinated by a tactical hub that reports back to an architect.
- **Persistent Compliance Monitoring**: A heartbeat process that wakes up every hour, inventories its "bag" of capability, and executes specialized checks against a data lake.
- **Complex Customer Support**: Routing deep research tasks to specialized workers while maintaining a lean, high-level context for the customer-facing director.

---

## 📂 Project Organization
Full specifications and implementation plans are in the `notes/` directory:

1. [02_BRS.md](notes/02_BRS.md): Business requirements and success metrics.
2. [03_FRS.md](notes/03_FRS.md): Functional specs and API definitions.
3. [05_ARCHITECTURE.md](notes/05_ARCHITECTURE.md): Technical deep-dive into the hub-and-spoke model.
4. [08_walkthrough.md](notes/08_walkthrough.md): Implementation roadmap.
5. [09_library_structure.md](notes/09_library_structure.md): Codebase organization.

## 🛠️ Implementation Phases
We are currently in **Phase 0 (Design Complete)**.
- **Phase 1**: Foundation & State (Schemas & Managers)
- **Phase 2**: Tactical Hub (LangGraph Orchestrator)
- **Phase 3**: The Architect's Tools (Node CRUD & Auditing)
- **Phase 4**: HUD & Telemetry (Observability)
- **Phase 5**: Production & Hardening (Persistence & HITL)

## 📜 License
Licensed under the **Apache License 2.0**.
