import os
from pypdf import PdfReader

class PDFParser:
    def extract_text(self, file_uri: str, section: str | None = None) -> dict:
        """Extract text content from a PDF file."""
        # Handle file:// URI and seeding paths
        file_path = file_uri.replace("file://", "")
        if not os.path.exists(file_path):
            return {"error": f"File not found: {file_path}. Try using a filename from the archive."}

        try:
            reader = PdfReader(file_path)
            text = ""
            for page in reader.pages:
                text += page.extract_text() + "\n"
            
            # Simple section filtering if provided (case-insensitive)
            if section and section.lower() in text.lower():
                # This is a very basic heuristic for demonstration
                parts = text.lower().split(section.lower())
                if len(parts) > 1:
                    relevant_text = parts[1][:2000] # Return first 2k chars of section
                    return {"text": relevant_text, "metadata": {"file": os.path.basename(file_path), "section": section}}

            return {
                "text": text[:5000],  # Limit to first 5k chars for LLM context
                "metadata": {"file": os.path.basename(file_path), "pages": len(reader.pages)},
            }
        except Exception as e:
            return {"error": str(e)}
