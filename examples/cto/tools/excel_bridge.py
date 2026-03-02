"""
ClawGraph Tool Mock: Excel Bridge
Authorized for: CMC, Patient Ops
"""

class ExcelBridge:
    def pull_sheet(self, file_uri: str) -> list:
        """Retrieve daily dosing or stability sheets."""
        print(f"📊 [ExcelBridge] Pulling sheet: {file_uri}")
        return [{"row": 1, "patient_id": "001", "dose": "50mg"}]

    def append_log(self, file_uri: str, data: dict):
        """Append a timestamped entry to the audit log."""
        print(f"📝 [ExcelBridge] Appending record to: {file_uri}")
