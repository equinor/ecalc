import argparse
import json
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal

REPO_ROOT = Path(__file__).parent.parent
CHANGELOG_DIR = REPO_ROOT / "changelog"
OUTPUT_PATH = REPO_ROOT / "docs" / "docs" / "changelog" / "nextgen.md"
YAML_REFERENCE_LINK = "../about/nextgen/yaml-reference.mdx"

ChangeKind = Literal["added", "changed", "deprecated", "removed"]
KINDS: tuple[ChangeKind, ...] = ("added", "changed", "deprecated", "removed")
KIND_TITLES: dict[ChangeKind, str] = {kind: kind.capitalize() for kind in KINDS}

UNRELEASED_FOLDER = "unreleased"
YAML_CHANGES_FILE = "yaml-changes.json"
NOTES_FILE = "notes.md"
RELEASE_FOLDER_PATTERN = re.compile(r"^(pre-)?v(\d+)\.(\d+)$")
NOTES_SECTION_PATTERN = re.compile(r"^## (.+)$", re.MULTILINE)
NOTES_TITLE_PATTERN = re.compile(r"\A# (.+)\n")

FRONTMATTER = """\
---
slug: "nextgen-changelog"
title: "NextGen"
authors: ecalc-team
tags: [release, eCalc, nextgen]
sidebar_position: 0
---
"""

INTRO = """\
# eCalc NextGen

Changes to the NextGen YAML types: `FLUIDS`, `PROCESS_SIMULATIONS`, `PUMP_PROCESS_SIMULATIONS` and `ENERGY_NETWORK`.
These are not available in legacy models, so they are not part of the release changelogs.
"""


@dataclass(frozen=True)
class YamlChange:
    kind: ChangeKind
    path: tuple[str, ...]
    description: str | None = None
    replaced_by: tuple[tuple[str, ...], ...] = ()


@dataclass
class Release:
    folder: str
    title: str
    sort_key: tuple[int, int, int]
    intro: str = ""
    notes: dict[ChangeKind, list[str]] = field(default_factory=lambda: {kind: [] for kind in KINDS})
    yaml_changes: list[YamlChange] = field(default_factory=list)

    @property
    def anchor(self) -> str:
        return self.folder.replace(".", "-")

    def is_empty(self) -> bool:
        return not self.intro and not self.yaml_changes and not any(self.notes.values())


def _parse_folder_name(name: str) -> tuple[str, tuple[int, int, int]]:
    if name == UNRELEASED_FOLDER:
        return "Unreleased", (1_000_000, 0, 0)
    match = RELEASE_FOLDER_PATTERN.match(name)
    if match is None:
        raise ValueError(f"Unexpected changelog folder '{name}'. Expected 'vX.Y', 'pre-vX.Y' or '{UNRELEASED_FOLDER}'.")
    is_pre, major, minor = match.group(1) is not None, int(match.group(2)), int(match.group(3))
    title = f"Before v{major}.{minor}" if is_pre else f"v{major}.{minor}"
    return title, (major, minor, 0 if is_pre else 1)


def _parse_notes(text: str, source: Path) -> tuple[str | None, str, dict[ChangeKind, list[str]]]:
    title_match = NOTES_TITLE_PATTERN.match(text)
    title = title_match.group(1).strip() if title_match else None
    if title_match:
        text = text[title_match.end() :]

    parts = NOTES_SECTION_PATTERN.split(text)
    intro = parts[0].strip()
    notes: dict[ChangeKind, list[str]] = {kind: [] for kind in KINDS}
    for heading, body in zip(parts[1::2], parts[2::2], strict=True):
        kind = heading.strip().lower()
        if kind not in KINDS:
            raise ValueError(
                f"{source}: unexpected section '## {heading}'. Expected one of {list(KIND_TITLES.values())}."
            )
        content = body.strip()
        if content:
            notes[kind].append(content)
    return title, intro, notes


def _parse_yaml_changes(data: dict, source: Path) -> list[YamlChange]:
    entries = []
    for raw in data["entries"]:
        if raw["kind"] not in KINDS:
            raise ValueError(f"{source}: unexpected kind '{raw['kind']}'.")
        entries.append(
            YamlChange(
                kind=raw["kind"],
                path=tuple(raw["path"]),
                description=raw.get("description"),
                replaced_by=tuple(tuple(path) for path in raw.get("replaced_by", [])),
            )
        )
    return entries


def load_releases(changelog_dir: Path) -> list[Release]:
    releases = []
    for folder in sorted(path for path in changelog_dir.iterdir() if path.is_dir()):
        title, sort_key = _parse_folder_name(folder.name)
        release = Release(folder=folder.name, title=title, sort_key=sort_key)

        notes_path = folder / NOTES_FILE
        if notes_path.exists():
            notes_title, release.intro, release.notes = _parse_notes(notes_path.read_text(), notes_path)
            if notes_title:
                release.title = notes_title

        yaml_changes_path = folder / YAML_CHANGES_FILE
        if yaml_changes_path.exists():
            release.yaml_changes = _parse_yaml_changes(json.loads(yaml_changes_path.read_text()), yaml_changes_path)

        if not release.is_empty():
            releases.append(release)
    return sorted(releases, key=lambda release: release.sort_key, reverse=True)


def added_in(releases: list[Release]) -> dict[str, str]:
    folders: dict[str, str] = {}
    for release in sorted(releases, key=lambda release: release.sort_key):
        if release.folder.startswith("pre-"):
            continue
        for entry in release.yaml_changes:
            path = ".".join(entry.path)
            if entry.kind == "added":
                folders[path] = release.folder
            elif entry.kind == "removed":
                folders.pop(path, None)
    return folders


def _resolve_anchor(path: tuple[str, ...], anchor_registry: dict[str, str]) -> str | None:
    for end in range(len(path), 0, -1):
        anchor = anchor_registry.get(".".join(path[:end]))
        if anchor is not None:
            return anchor
    return None


def _render_path(path: tuple[str, ...], anchor_registry: dict[str, str]) -> str:
    breadcrumb = " › ".join(f"`{segment}`" for segment in path)
    anchor = _resolve_anchor(path, anchor_registry)
    if anchor is None:
        return breadcrumb
    return f"[{breadcrumb}]({YAML_REFERENCE_LINK}#{anchor})"


def _render_yaml_change(entry: YamlChange, anchor_registry: dict[str, str]) -> str:
    line = _render_path(entry.path, anchor_registry)
    if entry.description:
        line = f"{line}: {entry.description}"
    if entry.replaced_by:
        replacements = " and ".join(_render_path(path, anchor_registry) for path in entry.replaced_by)
        line = f"{line}: replaced by {replacements}"
    return f"- {line}"


def render_release(release: Release, anchor_registry: dict[str, str]) -> str:
    lines = [f"## {release.title} {{/* #{release.anchor} */}}", ""]
    if release.intro:
        lines += [release.intro, ""]
    for kind in KINDS:
        notes = release.notes[kind]
        yaml_changes = [entry for entry in release.yaml_changes if entry.kind == kind]
        if not notes and not yaml_changes:
            continue
        lines += [f"### {KIND_TITLES[kind]} {{/* #{release.anchor}-{kind} */}}", ""]
        lines += notes
        lines += [_render_yaml_change(entry, anchor_registry) for entry in yaml_changes]
        lines.append("")
    return "\n".join(lines)


def render_nextgen_changelog(releases: list[Release], anchor_registry: dict[str, str]) -> str:
    sections = "\n".join(render_release(release, anchor_registry) for release in releases)
    return f"{FRONTMATTER}\n{INTRO}\n{sections}".rstrip("\n") + "\n"


def build_anchor_registry() -> dict[str, str]:
    from generate_yaml_asset_docs import generate_full_reference_markdown

    anchor_registry: dict[str, str] = {}
    generate_full_reference_markdown(anchor_registry=anchor_registry)
    return anchor_registry


def release_folder_name(version: str) -> str:
    match = re.fullmatch(r"(\d+)\.(\d+)\.(\d+)", version)
    if match is None:
        raise ValueError(f"Invalid release version '{version}'. Expected X.Y.Z.")
    major, minor, patch = match.groups()
    if patch != "0":
        raise ValueError(f"Release version '{version}' is a patch release. Only X.Y.0 releases are frozen.")
    return f"v{major}.{minor}"


def serialize_yaml_changes(changes: list[YamlChange]) -> str:
    entries = []
    for change in sorted(set(changes), key=lambda change: (KINDS.index(change.kind), change.path)):
        entry: dict = {"kind": change.kind, "path": list(change.path)}
        if change.description:
            entry["description"] = change.description
        if change.replaced_by:
            entry["replaced_by"] = [list(path) for path in change.replaced_by]
        entries.append(entry)
    return json.dumps({"entries": entries}, indent=2) + "\n"


def _has_content(folder: Path) -> bool:
    return any(path.name != ".gitkeep" for path in folder.iterdir())


def freeze_release(changelog_dir: Path, version: str) -> Path:
    release_dir = changelog_dir / release_folder_name(version)
    unreleased_dir = changelog_dir / UNRELEASED_FOLDER

    if unreleased_dir.is_dir() and _has_content(unreleased_dir):
        if release_dir.exists():
            raise ValueError(f"Both '{release_dir.name}' and '{UNRELEASED_FOLDER}' have entries. Merge them by hand.")
        unreleased_dir.rename(release_dir)
        (release_dir / ".gitkeep").unlink(missing_ok=True)

    unreleased_dir.mkdir(exist_ok=True)
    (unreleased_dir / ".gitkeep").touch()
    return release_dir


def _known_yaml_paths() -> set[tuple[str, ...]]:
    from generate_yaml_asset_docs import DocNode, build_yaml_asset_tree

    def walk(nodes: list[DocNode], path: tuple[str, ...]) -> set[tuple[str, ...]]:
        paths = set()
        for node in nodes:
            node_path = (*path, node.title)
            paths.add(node_path)
            paths |= walk(node.children, node_path)
        return paths

    return walk(build_yaml_asset_tree(include_fields=None), ())


def _parse_path(value: str) -> tuple[str, ...]:
    path = tuple(segment.strip() for segment in re.split(r"[.>›]", value))
    if not all(path):
        raise ValueError(
            f"Invalid path '{value}'. Give the YAML keywords separated by '.', e.g. PROCESS_PIPELINES.CHANGES."
        )
    return path


def add_yaml_change(changelog_dir: Path, change: YamlChange, known_paths: set[tuple[str, ...]]) -> Path:
    unknown = [path for path in change.replaced_by if path not in known_paths]
    if change.kind != "removed" and change.path not in known_paths:
        unknown.insert(0, change.path)
    if unknown:
        raise ValueError(
            f"Unknown YAML path: {', '.join('.'.join(path) for path in unknown)}. "
            "Use the keywords as titled in the YAML reference."
        )
    if change.replaced_by and change.kind != "removed":
        raise ValueError("replaced_by is only allowed for removed elements.")

    unreleased_dir = changelog_dir / UNRELEASED_FOLDER
    unreleased_dir.mkdir(exist_ok=True)
    yaml_changes_path = unreleased_dir / YAML_CHANGES_FILE
    existing = (
        _parse_yaml_changes(json.loads(yaml_changes_path.read_text()), yaml_changes_path)
        if yaml_changes_path.exists()
        else []
    )
    yaml_changes_path.write_text(serialize_yaml_changes([*existing, change]))
    return yaml_changes_path


def _release_please_version() -> str:
    return json.loads((REPO_ROOT / ".release-please-manifest.json").read_text())["."]


def main():
    parser = argparse.ArgumentParser(
        description="Generate the NextGen changelog page, add an entry or freeze a release."
    )
    subcommands = parser.add_subparsers(dest="command")

    add_parser = subcommands.add_parser("add", help=f"Add a YAML change to changelog/{UNRELEASED_FOLDER}.")
    add_parser.add_argument("kind", choices=KINDS)
    add_parser.add_argument("path", help="YAML keywords to the element, e.g. PROCESS_PIPELINES.CHANGES.")
    add_parser.add_argument("--description", help="What changed, mainly for 'changed'.")
    add_parser.add_argument(
        "--replaced-by", action="append", default=[], help="For 'removed': the path replacing it. Can be repeated."
    )

    freeze_parser = subcommands.add_parser(
        "freeze", help=f"Rename changelog/{UNRELEASED_FOLDER} to the release folder and start a new one."
    )
    freeze_parser.add_argument("--version", help="Release version X.Y.0. Defaults to .release-please-manifest.json.")
    args = parser.parse_args()

    if args.command == "add":
        change = YamlChange(
            kind=args.kind,
            path=_parse_path(args.path),
            description=args.description,
            replaced_by=tuple(_parse_path(path) for path in args.replaced_by),
        )
        print(f"Added to {add_yaml_change(CHANGELOG_DIR, change, _known_yaml_paths())}")
        return

    if args.command == "freeze":
        version = args.version or _release_please_version()
        release_dir = freeze_release(CHANGELOG_DIR, version)
        print(f"Froze v{version}: {release_dir if release_dir.exists() else 'no NextGen changes'}")
        return

    content = render_nextgen_changelog(load_releases(CHANGELOG_DIR), build_anchor_registry())
    OUTPUT_PATH.write_text(content)
    print(f"Generated: {OUTPUT_PATH}")


if __name__ == "__main__":
    try:
        main()
    except ValueError as error:
        sys.exit(f"error: {error}")
