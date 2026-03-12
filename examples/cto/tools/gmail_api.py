import json
import os
import datetime

class GmailAPI:
    def __init__(self, log_path: str = "examples/cto/artifacts/generated/comms_log.json"):
        self.log_path = os.path.abspath(log_path)
        os.makedirs(os.path.dirname(self.log_path), exist_ok=True)

    def _log_comm(self, entry: dict):
        history = []
        if os.path.exists(self.log_path):
            try:
                with open(self.log_path, 'r') as f:
                    history = json.load(f)
            except:
                pass
        
        history.append(entry)
        with open(self.log_path, 'w') as f:
            json.dump(history, f, indent=2)

    def send_alert(self, recipient: str, subject: str, body: str):
        """Send a guarded email alert and log it."""
        print(f"📧 [GmailAPI] Sending alert to: {recipient}")
        self._log_comm({
            "type": "alert",
            "timestamp": datetime.datetime.now().isoformat(),
            "recipient": recipient,
            "subject": subject,
            "body": body
        })

    def request_signature(self, physician_id: str, document_uri: str):
        """Trigger a human-in-the-loop signature request and log it."""
        print(f"✍️ [GmailAPI] Requesting signature from {physician_id}")
        self._log_comm({
            "type": "signature_request",
            "timestamp": datetime.datetime.now().isoformat(),
            "physician_id": physician_id,
            "document_uri": document_uri
        })
        return {"status": "sent", "request_id": f"SIG-{physician_id[:3]}-{datetime.datetime.now().strftime('%M%S')}"}
