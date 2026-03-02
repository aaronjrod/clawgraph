# CTO High-Fidelity Architecture (Refined)

This document visualizes the **Specialist-Bag** architecture of ClawGraph.

## 👁️ The Specialist Tier
In this model, each clinical specialist group operates within its own **Sovereign Workspace (Bag)**. The Architect (Super-Orchestrator) coordinates across these specialist boundaries.

```mermaid
graph TD
    subgraph "The Architect (Architect/Antigravity)"
        SO[RA Lead / Clinical Director]
    end

    SO -- "audit / repair" --> REG_BAG
    SO -- "audit / repair" --> CMC_BAG
    SO -- "audit / repair" --> OPS_BAG

    subgraph REG_BAG ["Regulatory Specialist Bag"]
        OR_REG[Tactical Hub]
        N_REG1[Protocol Benchmarking Node]
        N_REG2[IB Justification Node]
        N_REG3[Submission Vetting Node]
        OR_REG --- N_REG1
        OR_REG --- N_REG2
        OR_REG --- N_REG3
    end

    subgraph CMC_BAG ["CMC Specialist Bag"]
        OR_CMC[Tactical Hub]
        N_CMC1[CoA Parsing Node]
        N_CMC2[Facility Aggregation Node]
        OR_CMC --- N_CMC1
        OR_CMC --- N_CMC2
    end

    subgraph OPS_BAG ["Patient Ops Bag"]
        OR_OPS[Tactical Hub]
        N_OPS1[Daily Sheet Sync Node]
        N_OPS2[Abnormality Triage Node]
        N_OPS3[Document Integrity Node]
        OR_OPS --- N_OPS1
        OR_OPS --- N_OPS2
        OR_OPS --- N_OPS3
    end

    OPS_BAG -- "Site Abnormalities" --> REG_BAG
    REG_BAG -- "Protocol Updates" --> CMC_BAG
```

## 🚥 Specialist HUD View

| Bag | Specialist | Health | Last Major Signal | Task in Progress |
| :--- | :--- | :--- | :--- | :--- |
| **Regulatory** | RA Specialist | 🟢 OK | `DONE` | IB Justification |
| **CMC** | CMC Specialist | 🟡 RUNNING | `WORKING` | CoA Aggregation |
| **Patient Ops** | Clinical Coord| 🔴 ALERT | `NEED_INTERVENTION`| **Document Alignment** |

---

## 🛠️ Task-Level Atomic Skills
Each node in a bag is mapped to a highly specific skill file. For example, in the **Patient Ops Bag**, the `Document Integrity Node` uses:
- **Skill**: [`document_checker.md`](skills/patient_ops/document_checker.md)
- **Goal**: Specifically catch drug identifier mismatches (NM5072 vs NM5082).

This separation ensures that if the FDA changes a vetting rule, the Architect only needs to swap out one `.md` skill file in the **Regulatory Bag**, leaving the rest of the clinical system untouched.
