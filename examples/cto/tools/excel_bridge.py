import csv
import os
from typing import Any

class ExcelBridge:
    def pull_sheet(self, file_uri: str) -> list[dict[str, Any]]:
        """Retrieve daily dosing or stability sheets from a CSV/Excel source.
        
        Args:
            file_uri: The URI of the artifact to pull.
        """
        file_path = file_uri.replace("file://", "")

        if not os.path.exists(file_path):
            print(f"⚠️ [ExcelBridge] File not found: {file_path}")
            return [{"error": "File not found"}]

        print(f"📊 [ExcelBridge] Pulling real data from: {os.path.basename(file_path)}")
        try:
            with open(file_path, mode='r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                return list(reader)
        except Exception as e:
            return [{"error": str(e)}]

    def append_log(self, file_uri: str, data: dict[str, Any]):
        """Append a timestamped entry to the audit log."""
        file_path = file_uri.replace("file://", "")
        print(f"📝 [ExcelBridge] Persisting record to: {os.path.basename(file_path)}")
        
        with open(file_path, mode='a', encoding='utf-8') as f:
            f.write(f"{data}\n")
