import json
from pathlib import Path

import pytest

from src.generate_nextgen_changelog import (
    YamlChange,
    add_yaml_change,
    added_in,
    freeze_release,
    load_releases,
    render_nextgen_changelog,
)


def _write_release(
    changelog_dir: Path, folder: str, notes: str | None = None, yaml_changes: dict | None = None
) -> None:
    release_dir = changelog_dir / folder
    release_dir.mkdir(parents=True)
    if notes is not None:
        (release_dir / "notes.md").write_text(notes)
    if yaml_changes is not None:
        (release_dir / "yaml-changes.json").write_text(json.dumps(yaml_changes))


def _render(changelog_dir: Path, anchor_registry: dict[str, str] | None = None) -> str:
    return render_nextgen_changelog(load_releases(changelog_dir), anchor_registry or {})


def test_releases_are_ordered_newest_first_with_unreleased_on_top(tmp_path: Path):
    _write_release(tmp_path, "v15.10", notes="## Added\n\n- ten\n")
    _write_release(tmp_path, "v15.9", notes="## Added\n\n- nine\n")
    _write_release(tmp_path, "pre-v13.4", notes="# Groundwork before v13.4\n\nPreparation.\n")
    _write_release(tmp_path, "v13.4", notes="## Added\n\n- compressor\n")
    _write_release(tmp_path, "unreleased", notes="## Changed\n\n- next\n")

    content = _render(tmp_path)

    headings = [line for line in content.splitlines() if line.startswith("## ")]
    assert headings == [
        "## Unreleased {/* #unreleased */}",
        "## v15.10 {/* #v15-10 */}",
        "## v15.9 {/* #v15-9 */}",
        "## v13.4 {/* #v13-4 */}",
        "## Groundwork before v13.4 {/* #pre-v13-4 */}",
    ]


def test_notes_come_before_yaml_changes_in_each_kind(tmp_path: Path):
    _write_release(
        tmp_path,
        "v15.8",
        notes="## Removed\n\n- `EVENTS` is renamed to `CHANGES`.\n",
        yaml_changes={
            "entries": [
                {"kind": "added", "path": ["PROCESS_PIPELINES", "CHANGES"]},
                {
                    "kind": "removed",
                    "path": ["PROCESS_PIPELINES", "EVENTS"],
                    "replaced_by": [["PROCESS_PIPELINES", "CHANGES"]],
                },
            ],
        },
    )

    content = _render(tmp_path, anchor_registry={"PROCESS_PIPELINES": "process_pipelines"})

    assert content.endswith(
        "## v15.8 {/* #v15-8 */}\n\n"
        "### Added {/* #v15-8-added */}\n\n"
        "- [`PROCESS_PIPELINES` › `CHANGES`](../about/nextgen/yaml-reference.mdx#process_pipelines)\n\n"
        "### Removed {/* #v15-8-removed */}\n\n"
        "- `EVENTS` is renamed to `CHANGES`.\n"
        "- [`PROCESS_PIPELINES` › `EVENTS`](../about/nextgen/yaml-reference.mdx#process_pipelines): replaced by "
        "[`PROCESS_PIPELINES` › `CHANGES`](../about/nextgen/yaml-reference.mdx#process_pipelines)\n"
    )


def test_changed_entry_shows_description_and_unresolved_path_is_not_linked(tmp_path: Path):
    _write_release(
        tmp_path,
        "v15.7",
        yaml_changes={
            "entries": [{"kind": "changed", "path": ["DEFINITIONS", "TURBINES"], "description": "Moved."}],
        },
    )

    assert "- `DEFINITIONS` › `TURBINES`: Moved.\n" in _render(tmp_path)


def test_removed_entry_shows_replacement_and_description(tmp_path: Path):
    _write_release(
        tmp_path,
        "v15.7",
        yaml_changes={
            "entries": [
                {
                    "kind": "removed",
                    "path": ["A", "OLD"],
                    "replaced_by": [["A", "NEW"]],
                    "description": "Rename it.",
                }
            ],
        },
    )

    assert "- `A` › `OLD`: replaced by `A` › `NEW`. Rename it.\n" in _render(tmp_path)


def test_empty_unreleased_folder_is_skipped(tmp_path: Path):
    (tmp_path / "unreleased").mkdir()
    (tmp_path / "unreleased" / ".gitkeep").touch()

    assert "Unreleased" not in _render(tmp_path)


@pytest.mark.parametrize(
    "folder, notes, yaml_changes, message",
    [
        ("15.8", "## Added\n\n- x\n", None, "Unexpected changelog folder"),
        ("v15.8", "## Fixed\n\n- x\n", None, "unexpected section"),
        ("v15.8", None, {"entries": [{"kind": "moved", "path": ["A"]}]}, "unexpected kind"),
    ],
)
def test_invalid_changelog_is_rejected(
    tmp_path: Path, folder: str, notes: str | None, yaml_changes: dict | None, message: str
):
    _write_release(tmp_path, folder, notes=notes, yaml_changes=yaml_changes)

    with pytest.raises(ValueError, match=message):
        load_releases(tmp_path)


def test_committed_changelog_loads():
    releases = load_releases(Path(__file__).parents[2] / "changelog")

    assert releases


ADDED_CHANGES = YamlChange(kind="added", path=("PROCESS_PIPELINES", "CHANGES"))
REMOVED_EVENTS = YamlChange(
    kind="removed", path=("PROCESS_PIPELINES", "EVENTS"), replaced_by=(("PROCESS_PIPELINES", "CHANGES"),)
)
KNOWN_PATHS = {("PROCESS_PIPELINES",), ("PROCESS_PIPELINES", "CHANGES")}


def _files(directory: Path) -> dict[Path, bytes]:
    return {path.relative_to(directory): path.read_bytes() for path in directory.rglob("*") if path.is_file()}


def test_add_writes_sorted_entries_to_unreleased(tmp_path: Path):
    add_yaml_change(tmp_path, REMOVED_EVENTS, KNOWN_PATHS)
    add_yaml_change(tmp_path, ADDED_CHANGES, KNOWN_PATHS)
    add_yaml_change(tmp_path, ADDED_CHANGES, KNOWN_PATHS)

    assert json.loads((tmp_path / "unreleased" / "yaml-changes.json").read_text()) == {
        "entries": [
            {"kind": "added", "path": ["PROCESS_PIPELINES", "CHANGES"]},
            {
                "kind": "removed",
                "path": ["PROCESS_PIPELINES", "EVENTS"],
                "replaced_by": [["PROCESS_PIPELINES", "CHANGES"]],
            },
        ]
    }


@pytest.mark.parametrize(
    "change, message",
    [
        (
            YamlChange(kind="added", path=("PROCESS_PIPELINES", "UNKNOWN")),
            "Unknown YAML path: PROCESS_PIPELINES.UNKNOWN",
        ),
        (
            YamlChange(kind="removed", path=("PROCESS_PIPELINES", "EVENTS"), replaced_by=(("UNKNOWN",),)),
            "Unknown YAML path: UNKNOWN",
        ),
        (
            YamlChange(kind="changed", path=("PROCESS_PIPELINES",), replaced_by=(("PROCESS_PIPELINES", "CHANGES"),)),
            "only allowed for removed",
        ),
    ],
)
def test_add_rejects_invalid_changes(tmp_path: Path, change: YamlChange, message: str):
    with pytest.raises(ValueError, match=message):
        add_yaml_change(tmp_path, change, KNOWN_PATHS)


def test_freeze_moves_unreleased_to_release_and_starts_a_new_one(tmp_path: Path):
    add_yaml_change(tmp_path, ADDED_CHANGES, KNOWN_PATHS)
    (tmp_path / "unreleased" / "notes.md").write_text("## Changed\n\n- note\n")
    unreleased = _files(tmp_path / "unreleased")

    release_dir = freeze_release(tmp_path, "15.9.0")

    assert release_dir == tmp_path / "v15.9"
    assert _files(release_dir) == unreleased
    assert _files(tmp_path / "unreleased") == {Path(".gitkeep"): b""}


def test_freeze_is_idempotent(tmp_path: Path):
    add_yaml_change(tmp_path, ADDED_CHANGES, KNOWN_PATHS)
    freeze_release(tmp_path, "15.9.0")
    first = _files(tmp_path)

    freeze_release(tmp_path, "15.9.0")

    assert _files(tmp_path) == first


def test_freeze_without_entries_creates_no_release_folder(tmp_path: Path):
    (tmp_path / "unreleased").mkdir()
    (tmp_path / "unreleased" / ".gitkeep").touch()

    release_dir = freeze_release(tmp_path, "15.9.0")

    assert release_dir is not None and not release_dir.exists()
    assert (tmp_path / "unreleased" / ".gitkeep").exists()


def test_freeze_skips_patch_release(tmp_path: Path):
    add_yaml_change(tmp_path, ADDED_CHANGES, KNOWN_PATHS)
    before = _files(tmp_path)

    assert freeze_release(tmp_path, "15.9.1") is None
    assert _files(tmp_path) == before


def test_freeze_rejects_entries_in_both_release_and_unreleased(tmp_path: Path):
    _write_release(tmp_path, "v15.9", notes="## Added\n\n- x\n")
    add_yaml_change(tmp_path, ADDED_CHANGES, KNOWN_PATHS)

    with pytest.raises(ValueError, match="Merge them by hand"):
        freeze_release(tmp_path, "15.9.0")


@pytest.mark.parametrize("version", ["15.9", "v15.9.0", "15.9.x"])
def test_freeze_rejects_invalid_versions(tmp_path: Path, version: str):
    with pytest.raises(ValueError):
        freeze_release(tmp_path, version)


def test_added_in_maps_paths_to_latest_release_and_drops_removed(tmp_path: Path):
    _write_release(tmp_path, "pre-v13.4", yaml_changes={"entries": [{"kind": "added", "path": ["OLD"]}]})
    _write_release(
        tmp_path,
        "v15.7",
        yaml_changes={"entries": [{"kind": "added", "path": ["A", "B"]}, {"kind": "added", "path": ["C"]}]},
    )
    _write_release(
        tmp_path,
        "unreleased",
        yaml_changes={"entries": [{"kind": "removed", "path": ["C"]}, {"kind": "added", "path": ["D"]}]},
    )

    assert added_in(load_releases(tmp_path)) == {"A.B": "v15.7", "D": "unreleased"}
