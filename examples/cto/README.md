# CTO High-Fidelity README (Expert-View)

This document visualizes the **Specialist-Bag** hierarchy with granular task-level telemetry and tool authorization.

## 👁️ The Looming Architect View
The Super-Orchestrator manages a **6-Bag Sovereign Architecture**, coordinating between regulatory strategy, technical CMC data, and granular clinical operations.

## 👁️ The Looming Architect View
The Super-Orchestrator manages a **6-Bag Sovereign Architecture**. Every box below represents a 1st-class Agent Node.

```mermaid
graph TD
    SO[Architect: Clinical Director]

    subgraph CLIN_OPS ["Clinical Trial Ops (Daily Heartbeat)"]
        SYNC[Patient Tracking Sync]
        ONB[New Patient Onboarding]
        INV[Lab Invoice Vetting]
        INT[Master Integrity Checker]
        DEV[Deviation Reporting]
        TRIA[Abnormality Triage]
        SCRIB[Scribe Narration]
        INV_ALOC[Inventory Allocation]
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

    subgraph STRATEGY_LABEL ["Strategy & Labeling Bag"]
        RISK[Risk Assessment]
        NEG[Label Negotiation]
        CCDS[Core Data Sheet]
        USPI[Patient Leaflets]
    end

    subgraph REG_OPS ["Reg Ops (Publishing)"]
        PUBL[eCTD Publishing]
        FORM[Submission Formatting]
        GLOB[Global Coordination]
    end

    SO --- CLIN_OPS
    SO --- CLIN_REG
    SO --- CMC_REG
    SO --- STRATEGY_LABEL
    SO --- REG_OPS

    %% Feedback Loops
    STAB -- "trigger:ind_update" --> IND
    INT -- "trigger:regen_prot" --> PROT
    TRIA -- "trigger:safety_update" --> USPI
```

## 🚥 Cross-Bag Interrelationships (Super-Orchestrator Logic)
ClawGraph excels at the "Feedback Loops" that humans often miss:

1.  **Technical Pulse -> Clinical Update**: If `STAB` (CMC Bag) reports impurity drift, the **Architect** re-triggers `IND` (Clinical Reg) to update the safety justification.
2.  **Ops Feedback -> Protocol Change**: If `INT` (Clinical Ops) finds that Site Doctors can't fill the narration form in time, the **Architect** alerts `PROT` (Clinical Reg) to amend the protocol.
3.  **Entity Alignment**: If a patient data change occurs, the Architect signals **all** bags to run their `Document Integrity` nodes to ensure NM-class IDs match (e.g., catching **NM5072** vs **NM5082**).
4.  **Invoicing Safeguard**: The `INV` node in Clinical Ops checks lab bills against the `PROT` bag's Schedule of Assessments (SoA). If the lab over-bills, the agent blocks payment automatically.

## 🛠️ Predictive Orchestration (Next-Step Signaling)
Nodes in ClawGraph are proactive. Every `ClawOutput` includes a `next_steps_hint`.
*   **CMC Specialist**: "Stability passed. Hint: `trigger:ind_annual_update`."
*   **Patient Sync Agent**: "New patient enrolled. Hint: `trigger:onboarding_workflow`."
*   **Integrity Checker**: "Mismatch found. Hint: `trigger:halt_submission`, `trigger:alert_regulatory`."

---

## 💎 The "expert" check: Entity Alignment
When the `Document Integrity Node` (in Patient Ops) detects a drug name mismatch (**NM5072** vs **NM5082**):
1. It emits `NEED_INTERVENTION` + `summary` + `error_detail`.
2. The **Architect** receives a push notification on its HUD.
3. The Architect calls `audit_node("document_integrity")` to fetch the specific line numbers from Tier 3 records.
4. The Architect instructs the **Regulatory Bag** to regenerate the protocol and the **CMC Bag** to fix the CoA headers.
5. **Result**: The "Troubleshooting Debt" is handled by the AI, ensuring 100% submission accuracy.
