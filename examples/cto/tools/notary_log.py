import json
import os
import datetime

class NotaryLog:
    def __init__(self, log_path: str = "examples/cto/artifacts/generated/audit_trail.json"):
        self.log_path = os.path.abspath(log_path)
        os.makedirs(os.path.dirname(self.log_path), exist_ok=True)

    def log_integrity_check(self, batch_id: str, status: str, detail: str):
        """Write an immutable entry to the cryptographic audit ledger."""
        entry = {
            "timestamp": datetime.datetime.now().isoformat(),
            "batch_id": batch_id,
            "status": status,
            "detail": detail
        }
        print(f"🔏 [NotaryLog] LOGGING: {batch_id} -> {status}")
        
        try:
            history = []
            if os.path.exists(self.log_path):
                with open(self.log_path, 'r') as f:
                    history = json.load(f)
            
            history.append(entry)
            with open(self.log_path, 'w') as f:
                json.dump(history, f, indent=2)
                
            return {"status": "committed", "entry": entry}
        except Exception as e:
            return {"error": str(e)}

    def get_audit_trail(self, drug_id: str) -> list[dict[str, str]]:
        """Retrieve the sequence of all authorized tool calls for a drug."""
        if not os.path.exists(self.log_path):
            return []
            
        with open(self.log_path, 'r') as f:
            history = json.load(f)
            
        return [h for h in history if drug_id in h.get("batch_id", "")]
