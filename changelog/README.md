# NextGen changelog

Source for the NextGen changelog page, `docs/docs/changelog/nextgen.md`. `docs/scripts/generate-docs.sh` renders it
with `src/generate_nextgen_changelog.py`. The page is not committed, so edit the files here.

```
changelog/
  unreleased/           changes for the next release; the release PR renames it to vX.Y
  vX.Y/
    yaml-changes.json   YAML elements added, changed, deprecated or removed
    notes.md            hand-written notes
  pre-vX.Y/             notes for changes before vX.Y
```

Releases without NextGen changes have no folder.

## Creating a change

1. Add an entry for each NextGen YAML element (root or nested) that was added, changed, deprecated or removed:

   ```sh
   uv run python src/generate_nextgen_changelog.py add added ENERGY_NETWORK.UNITS.GENERATOR.CHANGES
   uv run python src/generate_nextgen_changelog.py add changed DEFINITIONS.TURBINES --description "Defined in PERFORMANCE_CURVES."
   uv run python src/generate_nextgen_changelog.py add removed PROCESS_PIPELINES.EVENTS --replaced-by PROCESS_PIPELINES.CHANGES
   ```

   A path is a list of YAML keywords, separated by `.` and written as titled in the YAML reference. The script checks
   that the path and each `--replaced-by` exist, except the path of a removed element. Fields inside a new element
   need no entry of their own.

2. Put anything a path cannot express in `unreleased/notes.md`, for example changed behaviour or results,
   explanations, or links to migration pages. The only sections allowed are `## Added`, `## Changed`,
   `## Deprecated` and `## Removed`. Text before the first section is shown under the release heading, and an
   optional `# Title` on the first line replaces that heading. Relative links resolve from `docs/docs/changelog/`.

3. Run `docs/scripts/generate-docs.sh`, check `docs/docs/changelog/nextgen.md`, then run `cd docs && npm run build`.
   The build fails on broken links.

Always write `yaml-changes.json` with the `add` command, never by hand.
