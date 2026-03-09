# Artifacts Architecture (v2 Draft)

In ClawGraph v2, we should formalize the artifact management system.

## Proposed Concepts

1. **Artifact Registry**: A formal object within `ClawBag` to track documents, rather than passing raw file URIs or generic strings.
2. **Version Control**: Built-in support for diffing and saving historical versions of documents edited by multiple nodes.
3. **Artifact Sub-types**: Differentiating between structured data files (JSON/YAML) and human-readable narrative files (Markdown/PDF).

*Note: Added per user request during the CTO mock-up development, where mock artifacts were extracted from hardcoded Python nodes into independent Markdown files on disk.*
