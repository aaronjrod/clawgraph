"""ClawNode decorator and metadata schema.

The @clawnode decorator captures node metadata and wraps the node function
to enforce ClawOutput schema compliance at runtime.

Spec ref: 10_clawnode_spec.md
"""

from __future__ import annotations

import functools
import logging
from typing import Any, Callable, Optional

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class ClawNodeMetadata(BaseModel):
    """Tier 1 metadata for a registered ClawNode. (F-REQ-3)

    This is what the Orchestrator sees in the manifest — descriptions and
    capabilities, never raw code (Tier 2) or artifacts (Tier 3).
    """

    id: str
    description: str
    bag: str
    provider: Optional[str] = None  # e.g., "anthropic", "openai", "google"
    model: Optional[str] = None  # e.g., "claude-3-5-sonnet", "gpt-4o"
    skills: list[str] = Field(default_factory=list)  # .md skill file paths
    tools: list[str] = Field(default_factory=list)  # Authorized tool identifiers
    tags: list[str] = Field(default_factory=list)  # Searchable labels
    requires: list[str] = Field(default_factory=list)  # Prerequisite artifact IDs
    escalation_policy: Optional[dict] = None  # {ttl_seconds, max_retries}
    audit_policy: Optional[dict] = None  # {always: bool, ...}


def clawnode(
    *,
    id: str,
    description: str,
    bag: str,
    provider: Optional[str] = None,
    model: Optional[str] = None,
    skills: Optional[list[str]] = None,
    tools: Optional[list[str]] = None,
    tags: Optional[list[str]] = None,
    requires: Optional[list[str]] = None,
    escalation_policy: Optional[dict] = None,
    audit_policy: Optional[dict] = None,
) -> Callable:
    """Decorator that registers a function as a ClawNode.

    Captures metadata and attaches it to the function as `_clawnode_metadata`.
    At runtime, the BagManager reads this metadata during `register_node()`.

    Usage:
        @clawnode(
            id="summarize_doc",
            description="Reads a document and returns a summary.",
            bag="research_ops",
            skills=["summarization.md"],
        )
        def summarize_doc(state: dict) -> ClawOutput:
            ...
    """
    metadata = ClawNodeMetadata(
        id=id,
        description=description,
        bag=bag,
        provider=provider,
        model=model,
        skills=skills or [],
        tools=tools or [],
        tags=tags or [],
        requires=requires or [],
        escalation_policy=escalation_policy,
        audit_policy=audit_policy,
    )

    def decorator(fn: Callable) -> Callable:
        @functools.wraps(fn)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            from clawgraph.core.models import ClawOutput

            result = fn(*args, **kwargs)

            # Schema enforcement: the node MUST return a ClawOutput.
            if not isinstance(result, ClawOutput):
                raise TypeError(
                    f"ClawNode '{id}' must return a ClawOutput, "
                    f"got {type(result).__name__}."
                )
            return result

        # Attach metadata for BagManager discovery.
        wrapper._clawnode_metadata = metadata  # type: ignore[attr-defined]
        return wrapper

    return decorator
