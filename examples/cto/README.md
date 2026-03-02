# CTO High-Fidelity README (Expert-View)

This document visualizes the **Specialist-Bag** hierarchy with granular task-level telemetry and tool authorization.

## 👁️ The Looming Architect View
The Super-Orchestrator manages a **6-Bag Sovereign Architecture**, coordinating between regulatory strategy, technical CMC data, and granular clinical operations.

## 👁️ The Looming Architect View
The Super-Orchestrator manages a **6-Bag Sovereign Architecture**. Every box below represents a 1st-class Agent Node.

## 👁️ The Looming Architect HUD
The Super-Orchestrator manages a **6-Bag Sovereign Architecture**. Every element below is a 1st-class Agent Node or Domain-Specific Skill, coordinated via a single tactical hub.

```mermaid
graph TD
    %% Architect Tier
    subgraph "Architect (Super-Orchestrator)"
        SO["<b>Looming Clinical Director</b><br/>(Cross-Bag Decision Intelligence)"]
    end

    %% Bag Tier
    SO --- CLIN_OPS
    SO --- CLIN_REG
    SO --- CMC_REG
    SO --- STRAT_LABEL
    SO --- REG_OPS
    SO --- MARKETING

    subgraph CLIN_OPS ["Clinical Trial Ops Bag"]
        SYNC[Patient Tracking Sync]
        ONB[New Patient Onboarding]
        INV[Lab Invoice Vetting]
        INT[Master Integrity Checker]
        DEV[Deviation Reporting]
        TRIA[Abnormality Triage]
        SCRIB[Scribe Narration]
    end

    subgraph CLIN_REG ["Clinical Regulatory Bag"]
        IND[IND Submissions]
        PROT[Protocol Development]
        IB[Investigator Brochure]
        ANN[Annual Reports]
    end

    subgraph CMC_REG ["CMC Regulatory Bag"]
        MOD3[Module 3 Tech Docs]
        STAB[Stability Trending]
        SUB[Substance Validation]
    end

    subgraph STRAT_LABEL ["Strategy & Labeling Bag"]
        RISK[Risk Assessment]
        NEG[Label Negotiation]
        CCDS[Core Data Sheet]
        USPI[Patient Leaflets]
    end

    subgraph REG_OPS ["Reg Ops Bag"]
        PUBL[eCTD Publishing]
        FORM[Submission Formatting]
        GLOB[Global Coordination]
    end

    subgraph MARKETING ["Marketing Bag"]
        PR[Press Release Writer]
    end

    %% Styling for "Impressive" look
    style SO fill:#f9f,stroke:#333,stroke-width:4px,color:#000
    style CLIN_OPS fill:#e1f5fe,stroke:#01579b
    style CLIN_REG fill:#e1f5fe,stroke:#01579b
    style CMC_REG fill:#fff3e0,stroke:#e65100
    style STRAT_LABEL fill:#f3e5f5,stroke:#4a148c
    style REG_OPS fill:#f1f8e9,stroke:#1b5e20
    style MARKETING fill:#fce4ec,stroke:#880e4f
```

## 🚥 Cross-Bag Delegation (SO-Mediated Logic)
ClawGraph preserves bag sovereignty. Communication is always mediated by the Super-Orchestrator (SO):

1.  **Technical Pulse -> Clinical Update**: If `STAB` (CMC Bag) emits structural drift data, the **SO** re-triggers the `IND` (Clinical Reg) node to update the safety justification.
2.  **Ops Signal -> Strategic Alert**: If `INT` (Clinical Ops) detects an NM-ID mismatch (NM5072 vs NM5082), the **SO** pauses the `PUBL` (Reg Ops) workflow and tasks the `PROT` (Clinical Reg) bag with a correction.
3.  **Sovereignty Rule**: A node in one bag cannot see or trigger a node in another. It reports to the **Architect**, which maintains the global "State of the Submission."

## 🛠️ Predictive Signaling (Hints for the SO)
Nodes emit `next_steps_hint` as tactical recommendations.
*   **Medical Scribe**: "Visit complete. Hint: `check:daily_sync`."
*   **Stability Agent**: "New impurity threshold met. Hint: `check:mfg_comparability`."
*   **SO Logic**: Receives hints -> Filters through Global Strategy -> Delegates to the next Sovereign Bag.

---

## 💎 The "expert" check: Entity Alignment
When the `Document Integrity Node` (in Patient Ops) detects a drug name mismatch (**NM5072** vs **NM5082**):
1. It emits `NEED_INTERVENTION` + `summary` + `error_detail`.
2. The **Architect** receives a push notification on its HUD.
3. The Architect calls `audit_node("document_integrity")` to fetch the specific line numbers from Tier 3 records.
4. The Architect instructs the **Regulatory Bag** to regenerate the protocol and the **CMC Bag** to fix the CoA headers.
5. **Result**: The "Troubleshooting Debt" is handled by the AI, ensuring 100% submission accuracy.
