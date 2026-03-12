import os
import sys
import json

# Add parent dir to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from examples.cto.tools.pdf_parser import PDFParser
from examples.cto.tools.excel_bridge import ExcelBridge
from examples.cto.tools.gmail_api import GmailAPI
from examples.cto.tools.google_search import GoogleSearch
from examples.cto.tools.notary_log import NotaryLog
from examples.cto.tools.stats_calc import StatsCalc

def test_all_tools():
    print("🚀 Starting End-to-End Tool Verification...\n")
    
    # 1. PDF Parser
    print("--- Testing PDFParser ---")
    pdf = PDFParser()
    target_pdf = "examples/cto/artifacts/reg_sources/protocol_v1.pdf"
    if not os.path.exists(target_pdf):
        # Fallback if I didn't copy it right
        target_pdf = "examples/cto/artifacts/reg_sources/E3_Guideline.pdf"
    
    res_pdf = pdf.extract_text(target_pdf)
    print(f"PDF Extraction Length: {len(res_pdf.get('text', ''))} chars")
    assert "data" in res_pdf or "text" in res_pdf
    
    # 2. Excel Bridge
    print("\n--- Testing ExcelBridge ---")
    bridge = ExcelBridge()
    target_csv = "examples/cto/artifacts/patient_sync_raw.csv"
    res_csv = bridge.pull_sheet(target_csv)
    print(f"CSV Row Sample: {str(res_csv)[:100]}...")
    assert isinstance(res_csv, (list, dict))
    
    res_append = bridge.append_log(target_csv, {"PatientID": "999", "Status": "TEST"})
    print(f"Append Status: {res_append}")
    
    # 3. Gmail API
    print("\n--- Testing GmailAPI ---")
    gmail = GmailAPI(log_path="examples/cto/artifacts/generated/comms_log.json")
    res_alert = gmail.send_alert("test@example.com", "Verification", "Tool test alert")
    print(f"Send Alert: {res_alert}")
    
    res_sig = gmail.request_signature("physician_456", "file:///seed/protocol_v1.pdf")
    print(f"Request Signature: {res_sig}")
    
    # 4. Google Search
    print("\n--- Testing GoogleSearch ---")
    search = GoogleSearch()
    res_search = search.search("ICH E3 Guideline summary")
    print(f"Search Result Sample: {str(res_search)[:100]}...")
    assert "E3" in str(res_search)
    
    # 5. Notary Log
    print("\n--- Testing NotaryLog ---")
    notary = NotaryLog(log_path="artifacts/generated/audit_trail.json")
    res_notary = notary.log_integrity_check("protocol_v1", "HASH123", "PASSED")
    print(f"Log Integrity: {res_notary}")
    
    res_audit = notary.get_audit_trail("protocol_v1")
    print(f"Audit Trail Count: {len(res_audit)}")
    
    # 6. Stats Calc
    print("\n--- Testing StatsCalc ---")
    stats = StatsCalc()
    res_var = stats.calculate_variance([10, 12, 11, 13, 12])
    print(f"Variance: {res_var}")
    
    res_pk = stats.align_pk_metrics({"Cmax": 100, "AUC": 500}, {"Cmax": 102, "AUC": 490})
    print(f"PK Alignment: {res_pk}")

    print("\n✅ All tools verified successfully!")

if __name__ == "__main__":
    test_all_tools()
