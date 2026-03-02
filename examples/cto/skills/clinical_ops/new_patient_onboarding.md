# Task: New Patient Onboarding

## Role
You coordinate the "Welcome Package" for new trial participants.

## Logic
- **Trigger**: New enrollment detected in the Sync Excel.
- **Action 1 (Patient)**: Release the **Informed Consent Form (ICF)**.
- **Action 2 (Doctors)**: Release the Medical Scribe templates and the **Schedule of Assessments (SoA)**.
- **Action 3 (Lab)**: Notify the lab of the specific testing date/time for collection.

## Signals
- **DONE**: Documents released to all 3 stakeholders.
- **NEED_INTERVENTION**: Physician signature missing on ICF.
