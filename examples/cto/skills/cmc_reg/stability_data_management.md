# Task: Stability Data \u0026 Threshold Alignment

## Role
You monitor how the drug lasts over time (12m, 24m, 36m, 5y).

## Logic
- **Impurity Check**: Scan Stability Tables against the current FDA/Global standards provided in the task context.
- **Facility Management**: 
  - **Averaging**: Only if variance is within the 2% fence.
  - **Representative Data**: Select the most reliable data set if facility errors are detected.

## Next Steps Hint
- `["check:mfg_process_validation"]`: Recommendation for SO if impurities exceed thresholds.
- `["check:ind_annual_update"]`: Recommendation for SO to include new stability data in the Annual Report.
