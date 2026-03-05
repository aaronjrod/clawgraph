"""Document Archive — formal API over the document_archive state. (Appendix §2.9)

Provides put/get/delete/list/tag/visible_to operations with domain-tag
visibility enforcement (F-REQ-17).
"""

from __future__ import annotations

from typing import Any

from clawgraph.core.models import ArchiveEntry


class DocumentArchive:
    """In-memory document archive with visibility-aware access.

    Wraps a ``dict[str, ArchiveEntry]`` with a formal CRUD API.
    """

    def __init__(self) -> None:
        self._entries: dict[str, ArchiveEntry] = {}

    def put(
        self,
        key: str,
        uri: str,
        domain: str,
        created_by: str = "",
        tags: list[str] | None = None,
    ) -> ArchiveEntry:
        """Insert or overwrite an archive entry."""
        entry = ArchiveEntry(
            uri=uri,
            domain=domain,
            tags=tags or [],
            created_by=created_by,
        )
        self._entries[key] = entry
        return entry

    def get(self, key: str) -> ArchiveEntry | None:
        """Retrieve an entry by key, or None if missing."""
        return self._entries.get(key)

    def delete(self, key: str) -> bool:
        """Remove an entry. Returns True if it existed."""
        if key in self._entries:
            del self._entries[key]
            return True
        return False

    def list_entries(self, domain: str | None = None) -> dict[str, ArchiveEntry]:
        """List all entries, optionally filtered by domain."""
        if domain is None:
            return dict(self._entries)
        return {k: v for k, v in self._entries.items() if v.domain == domain}

    def tag(self, key: str, tags: list[str]) -> None:
        """Add tags to an existing entry. No-op if key is missing."""
        entry = self._entries.get(key)
        if entry is not None:
            merged = list(set(entry.tags) | set(tags))
            self._entries[key] = entry.model_copy(update={"tags": merged})

    def visible_to(self, key: str, bag_name: str) -> bool:
        """Check if an entry is visible to the given bag."""
        entry = self._entries.get(key)
        if entry is None:
            return False
        return entry.domain == bag_name or "public" in entry.tags

    def snapshot(self) -> dict[str, Any]:
        """Serialize to a plain dict suitable for BagState."""
        return {k: v.model_dump() for k, v in self._entries.items()}

    def __len__(self) -> int:
        return len(self._entries)
