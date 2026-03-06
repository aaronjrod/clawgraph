"""Document node pattern — CRUD helpers with precision-edit semantics.

Spec ref: 06_patterns.md S8.1-8.3
"""

from __future__ import annotations

from dataclasses import dataclass

from clawgraph.core.models import ClawOutput, Signal


@dataclass
class DocumentEdit:
    """A precision edit to apply to a document (Part 8, S8.1).

    Instead of full rewrites, agents produce targeted edits -- line-level or
    section-level diffs -- that a DocumentArchive manager can apply atomically.
    """

    section: str  # Section or line range identifier, e.g., "Section 3" or "L45-60"
    old_content: str | None = None  # What to replace (None = insert)
    new_content: str = ""  # Replacement content
    reason: str = ""  # Why this edit was made


class DocumentNode:
    """Helpers for CRUD document operations (Part 8).

    Enforces the precision-edit pattern: updates return diffs, not full rewrites.
    Use in combination with @clawnode for the function signature.

    Usage::

        dn = DocumentNode(node_id="clinical_editor")

        # CREATE
        return dn.create(uri="uri://protocol_v1.md", summary="Drafted protocol v1.")

        # READ
        return dn.read(finding="Stability mismatch in Section 4.2.",
                       uri="uri://protocol_v1.md")

        # UPDATE (precision edit)
        edits = [DocumentEdit(section="Section 3", old_content="old", new_content="new")]
        return dn.update(uri="uri://protocol_v2.md", edits=edits,
                         summary="Updated impurities table.")

        # REWRITE
        return dn.rewrite(uri="uri://protocol_v2.md",
                          summary="Complete restructuring for global alignment.")
    """

    def __init__(self, node_id: str) -> None:
        self.node_id = node_id

    def create(self, uri: str, summary: str) -> ClawOutput:
        """Phase: CREATE -- Draft initial document."""
        return ClawOutput(
            signal=Signal.DONE,
            node_id=self.node_id,
            orchestrator_summary=f"Created: {summary}",
            result_uri=uri,
        )

    def read(self, finding: str, uri: str) -> ClawOutput:
        """Phase: READ -- Scan for specific data and report finding."""
        return ClawOutput(
            signal=Signal.DONE,
            node_id=self.node_id,
            orchestrator_summary=f"Found: {finding}",
            result_uri=uri,
        )

    def update(
        self,
        uri: str,
        edits: list[DocumentEdit],
        summary: str,
    ) -> ClawOutput:
        """Phase: UPDATE -- Apply precision patches (S8.1).

        Returns a DONE signal with edit metadata. The edits themselves
        are stored externally; the ClawOutput only contains the summary.
        """
        edit_descriptions = [f"[{e.section}]: {e.reason or 'Updated'}" for e in edits]
        detail = "; ".join(edit_descriptions)
        return ClawOutput(
            signal=Signal.DONE,
            node_id=self.node_id,
            orchestrator_summary=f"Updated ({len(edits)} edits): {summary}. Edits: {detail}",
            result_uri=uri,
        )

    def rewrite(self, uri: str, summary: str) -> ClawOutput:
        """Phase: REWRITE -- Full document restructure (rare)."""
        return ClawOutput(
            signal=Signal.DONE,
            node_id=self.node_id,
            orchestrator_summary=f"Rewrote: {summary}",
            result_uri=uri,
        )
