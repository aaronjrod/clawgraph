"""
ClawGraph Tool Mock: Gmail API
Authorized for: Patient Ops
"""

class GmailAPI:
    def send_alert(self, recipient: str, subject: str, body: str):
        """Send a guarded email alert."""
        print(f"📧 [GmailAPI] Sending alert to: {recipient}")
        print(f"Subject: {subject}")

    def request_signature(self, physician_id: str, document_uri: str):
        """Trigger a human-in-the-loop signature request."""
        print(f"✍️ [GmailAPI] Requesting signature from {physician_id} for {document_uri}")
