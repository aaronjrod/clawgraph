# CTO Workspace: Tool Definitions

These tools represent the **deterministic capabilities** authorized for use by Agent Nodes in the Clinical Workspace.

## 🔎 Information Tools

### `google_search`
- **Capability**: Real-time internet access via Serper/Google Search API.
- **Usage**: Benchmarking protocols against competitors, researching physiological mechanisms for abnormalities.
- **Constraints**: Results are summarized to 1k tokens.

### `pdf_parser`
- **Capability**: High-fidelity Extraction of text, tables, and metadata from PDF submissions.
- **Usage**: Reading FDA 21 CFR documents, competitive protocols, and batch certificates (CoAs).

## 📊 Data & Ops Tools

### `excel_bridge`
- **Capability**: Read/Write access to local and cloud-based Excel sheets (.xlsx).
- **Usage**: Updating Patient Dosing Sheets, logging Batch variance data.
- **Constraint**: Every write operation creates a timestamped `audit_log` entry.

### `stats_calc`
- **Capability**: Precision statistical engine for volatility, variance, and trend analysis.
- **Usage**: CMC stability trending, calculating impurity thresholds (0.5% vs 0.1%).

### `gmail_api`
- **Capability**: Authenticated access to the clinical workspace email.
- **Usage**: Sending "Deviation Alerts" to CROs, requesting Physician signatures on abnormalities.
- **Guardrail**: All emails require `HOLD_FOR_HUMAN` approval if the recipient is external to the `@sponsor.com` domain.

## 📜 Legal & Audit Tools

### `notary_log`
- **Capability**: Write-only ledger for cryptographically signed entity vetting.
- **Usage**: Logging the "NM5082 vs NM5072" integrity check results.
- **Value**: Provides an immutable audit trail for Regulatory submissions.
