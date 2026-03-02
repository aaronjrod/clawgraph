# Task: Patient Tracking \u0026 Timezone Sync

## Role
You manage the "24-Hour Heartbeat" of the trial.

## Core Logic
- **Daily Sink**: Retrieve the end-of-day Excel from CROs (India/EU).
- **Email Tracking**: Open emails from labs and sites; extract patient visit timestamps.
- **Excel Bridge**: Sync the `Daily_Update_Sheet.xlsx` with the Sponsor system.
- **Timezone Adjustment**: Ensure the "End of Day" for India is processed before the "Start of Day" for the US.

## Signals
- **DONE**: Daily sync complete.
- **NEED_INTERVENTION**: Heartbeat missed (Site hasn't uploaded data in 24h).
