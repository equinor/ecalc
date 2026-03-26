"""
Dataclasses that describe the structure of the YAML reference page.

PageDoc → SectionDoc → ItemDoc forms a tree matching the YAML keyword hierarchy.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class ItemDoc:
    """One keyword in the YAML hierarchy.

    Maybe a leaf (no children) or a branch (with children).
    All siblings share the same indentation level regardless.
    """

    keyword: str
    required: bool
    type_label: str
    default: str
    description: str
    anchor: str
    depth: int = 0
    is_variant: bool = False
    children: list[ItemDoc] = field(default_factory=list)


@dataclass
class SectionDoc:
    """A top-level section that gets a Markdown heading."""

    keyword: str
    anchor: str
    depth: int
    description: str
    type_label: str = ""
    required: bool = False
    items: list[ItemDoc] = field(default_factory=list)
    example: str = ""


@dataclass
class PageDoc:
    """The full YAML reference page."""

    title: str
    sections: list[SectionDoc] = field(default_factory=list)
