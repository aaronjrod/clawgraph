# Primary Source Documents Repository (High-Fidelity)

This repository contains the ground-truth data and regulatory frameworks driving the CTO simulation.

## 1. Canonical Regulatory Sources
Primary statutory PDFs located in `examples/cto/artifacts/reg_sources/` (see `tagging_manifest.json` for metadata).
- **FDA 356h**: NDA Application framework.
- **ICH E3**: Clinical Study Report standards.
- **ICH M4Q**: CMC Quality summary taxonomy.

## 2. Experimental Seed Data
Granular technical seeds used by nodes for reasoning and synthesis:
- **protocol_v1.md**: Trial design, endpoints, and ICH Q3 impurity thresholds.
- **stability_test_report_q1.md**: CMC analytical batch data and drift logs.
- **patient_sync_raw.csv**: High-fidelity trial database (N=12) with IGA scores and SAE flags.

## 3. Submission Infrastructure
- **unformatted_modules_v2.md**: Draft CTD Module structure (2-5).
- **source_docs_v1.md**: This manifest.

*Note: All generated node outputs are stored in `examples/cto/artifacts/generated/`.*