---
description: Automated LaTeX compilation for high-fidelity regulatory artifacts
---
# Workflow: High-Fidelity LaTeX Compilation

This workflow defines the steps to transform structured simulation outputs into professional, submission-grade PDF documents.

## Prerequisites
- `pdflatex` or `xelatex` installed on the system.
- LaTeX templates located in `examples/cto/templates/regulatory/`.

## Steps

1. **Structured Data Extraction**
   Ensure the node output is in **High-Fidelity Markdown** or **JSON** format, following ICH/FDA structural requirements (e.g., E3 Patient Narrative demographics).

2. **Template Mapping**
   Select the appropriate `.tex` template:
   - `patient_narrative_e3.tex`
   - `quality_summary_m4q.tex`
   - `admin_cover_letter.tex`

3. **LaTeX Generation**
   // turbo
   Run a conversion script (e.g., `markdown_to_latex.py`) to inject the experimental data into the LaTeX environment.

4. **Compilation**
   // turbo
   Execute `pdflatex -interaction=nonstopmode output.tex` in the artifact's generated directory.

5. **Post-Processing**
   Move the resulting `.pdf` to the `document_archive` and emit a `Signal.DONE` with the PDF's `result_uri`.

## Usage
Trigger this workflow from a `pdf_compiler` node or as a manual post-simulation step to generate "investor-ready" documentation.
