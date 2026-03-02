# Skill Bunch: Lab, Medical, \u0026 Marketing

## 🧪 Lab Operations Specialist
- **Task**: Daily pick-up coordination.
- **Expert Rule**: Calculate test invoices daily. Compare the "Lab Received" log against the "Schedule of Assessments" (SoA).
- **Signal**: `FAILED` if the lab performs "Additional Tests" not authorized by the SoA.

## 🩺 Doctor / Medical Scribe Agent
- **Task**: Source Document Narration.
- **Narrative**: "Patient came in [TIME], received [ML] of NM5082, had [ML] blood draw, left at [TIME]."
- **Patient Fill**: Prompt patients daily: "How are symptoms? Getting better? What do you feel?"
- **Signal**: `WAIT_FOR_HUMAN` for adverse event signatures.

## 📣 Marketing \u0026 Press Agent
- **Task**: Press Release Generation.
- **Strategy**: Brag about "Starting Clinical Trial," "Positive Patient Signal," or "Phase 3 Completion."
- **Expert Rule**: NEVER include raw patient data; only summarized outcomes vetting by Regulatory Affairs.
- **Signal**: `DONE` once Regulatory Specialist approves the draft.
