"""SkillsContextManager -- loads .md skill files for node prompt injection.

Skill files are markdown documents that contain domain-specific
instructions for a node. They are referenced by path in the @clawnode
decorator's `skills` field and loaded at dispatch time by the
Orchestrator to inject domain context into the node's prompt.

Architecture ref: 06_patterns.md S3, 05_ARCHITECTURE.md S10.5
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from clawgraph.bag.node import ClawNodeMetadata

logger = logging.getLogger(__name__)


class SkillsContextManager:
    """Reads .md skill files and assembles prompt context for nodes.

    The Super-Orchestrator stores skill definitions as markdown files
    in a skills directory. Each node can reference one or more skills
    via its metadata. This manager resolves those references and
    returns concatenated prompt text.

    Usage:
        scm = SkillsContextManager(skills_dir="examples/cto/skills")
        context = scm.load_skills_for_node(node_metadata)
    """

    def __init__(self, skills_dir: str | Path | None = None) -> None:
        self._skills_dir = Path(skills_dir) if skills_dir else None
        self._cache: dict[str, str] = {}

    @property
    def skills_dir(self) -> Path | None:
        return self._skills_dir

    def set_skills_dir(self, skills_dir: str | Path) -> None:
        """Set or update the skills directory. Clears the cache."""
        self._skills_dir = Path(skills_dir)
        self._cache.clear()
        logger.info("Skills directory set to: %s", self._skills_dir)

    def load_skill(self, skill_path: str) -> str:
        """Load a single skill file by relative path.

        Args:
            skill_path: Relative path to the skill file from skills_dir
                        (e.g., "clinical_ops/patient_tracking_sync.md").

        Returns:
            The file contents as a string, or an error message if
            the file cannot be read.

        Raises:
            ValueError: If no skills_dir is configured.
        """
        if self._skills_dir is None:
            raise ValueError("No skills_dir configured. Call set_skills_dir() first.")

        # Check cache first.
        if skill_path in self._cache:
            return self._cache[skill_path]

        full_path = self._skills_dir / skill_path

        if not full_path.is_file():
            msg = f"<skill not found: {skill_path}>"
            logger.warning("Skill file not found: %s", full_path)
            return msg

        try:
            content = full_path.read_text(encoding="utf-8")
            self._cache[skill_path] = content
            logger.debug("Loaded skill: %s (%d bytes)", skill_path, len(content))
            return content
        except OSError as exc:
            msg = f"<skill read error: {skill_path}: {exc}>"
            logger.error("Failed to read skill file %s: %s", full_path, exc)
            return msg

    def load_skills_for_node(
        self,
        node_meta: ClawNodeMetadata | dict[str, Any],
    ) -> str:
        """Load all skills referenced by a node's metadata.

        Args:
            node_meta: A ClawNodeMetadata instance or a dict with a 'skills' key.

        Returns:
            Concatenated skill contents, separated by section headers.
            Returns an empty string if the node has no skills.
        """
        if isinstance(node_meta, ClawNodeMetadata):
            skills_list = node_meta.skills
        else:
            skills_list = node_meta.get("skills", [])

        if not skills_list:
            return ""

        sections: list[str] = []
        for skill_path in skills_list:
            content = self.load_skill(skill_path)
            sections.append(f"--- Skill: {skill_path} ---\n{content}")

        return "\n\n".join(sections)

    def clear_cache(self) -> None:
        """Clear the skill file cache."""
        self._cache.clear()

    def __repr__(self) -> str:
        dir_str = str(self._skills_dir) if self._skills_dir else "<not set>"
        return f"SkillsContextManager(skills_dir='{dir_str}', cached={len(self._cache)})"
