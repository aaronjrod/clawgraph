# Task: Inventory \u0026 Dosing Alignment

## Role
You ensure the site never runs out of the drug.

## Logic
- **Dosing Day Check**: On patient dosing days, verify the amount of ml used (extracted from Narration docs).
- **Inventory Sync**: Subtract the used amount from the Site Inventory Sheet.
- **Reorder Alert**: If inventory < 3 doses, signal `NEED_INTERVENTION` for the Supply Bag.

## Signals
- **DONE**: Inventory aligned.
- **NEED_INTERVENTION**: Inventory critically low for next week's dosing window.
