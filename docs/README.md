# Get started

This website is built using [Docusaurus 3](https://docusaurus.io/), a modern static website generator.

In order to edit the docs you need either [NodeJS (recommended)](https://nodejs.org/en/download/) together with
the package manager [npm]. See [local development](#local-development) for details on how to get started with local development.

## How it works

The Doc navigation is dynamically generated based on the file structure under ./docs. This is where you normally
would edit the markdown-files (.md). Using a modern IDE you can preview the markdown files without running a local
development environment. The difference is that LaTeX, abominations and some custom JavaScript will not be rendered.

Docusaurus is easy to use, and it can be useful to skim through the [Docusaurus Docs](https://docusaurus.io/docs/category/getting-started)
before getting started, just to get an overview. Here we will cover a few topics that is more or less relevant for us:

### Document structure

A markdown file can start with a metadata section such as:

~~~~~~~~markdown
---
sidebar_position: 1
title: eCalc modelling
description: An introduction to eCalc modelling
keywords:
  - docs
---
~~~~~~~~

This can help with search engine optimization, menu ordering, tagging, and much more. Please see the reference documentation
[here](https://docusaurus.io/docs/api/plugins/@docusaurus/plugin-content-docs#markdown-front-matter) for more details.

The rest of the document is pure markdown or markdown and JavaScript/React if needed. In case of JavaScript the file
ending will be .mdx.

### Links

It is advised to use relative links to other markdown-pages. This is to avoid issues when building the page, which will
make the local build and the GitHub Pipeline fail. E.g. you have the markdown-files /docs/modelling/index.md,
and you want to refer to /docs/getting_started/index.md:

~~~~~~~~markdown
[Getting started](../getting_started/index)
~~~~~~~~

This will provide the correct path

### Images

It is advised to put images into the same location or a sub-folder in the same location where it is actually used.
This is because of versioned docs, so we can't rely on the static folder for this. However, the static folder will
be used if we create other pages that are not part of the versioned docs.

### LaTeX

LaTeX is supported in mdx-files only using KaTeX/MathML plugins. See [Math equations](https://docusaurus.io/docs/markdown-features/math-equations)
if the official docs for more info.

### Versioning

Each version of the docs is a separate build, published to the `gh-pages` branch by
[publish-docs.yml](../.github/workflows/publish-docs.yml) using [deploy-versioned-docs.mjs](scripts/deploy-versioned-docs.mjs):

| Path                  | Content                                                              | Published when                      |
|-----------------------|----------------------------------------------------------------------|-------------------------------------|
| `/ecalc/`             | Redirect to the latest release, keeping the path ([static-root](static-root/index.html)). Also served as `404.html`, so old links such as `/ecalc/docs/...` keep working | Every push to main |
| `/ecalc/vX.Y/`        | One folder per minor release, the 5 newest are kept. Patches overwrite their minor | Every release |
| `/ecalc/next/`        | Unreleased docs from main                                            | Every push to main                  |
| `/ecalc/versions.json`| List of published versions                                           | Every deploy                        |

The root redirect, the version dropdown in the navbar and the banner on outdated versions all read `versions.json`
in the browser, so a new release is the default as soon as it is published, and older builds always show the current
list of versions. The dropdown and banner are hidden when running locally.

A build is configured with the environment variables `DOCS_BASE_URL` (default `/ecalc/`) and `DOCS_VERSION`
(default `local`). Publishing only happens from CI: pushes to main publish `next`, and release-please publishes
each release.

### Blog / Release notes

The blog functionality is currently used for release notes, and is named this on the top menu bar. This is a
business-related release note that should also link to migration guides and GitHub release notes.

## Local development

Some pages are generated from the code, and must be generated before starting or building the docs.
See [Generated docs](#generated-docs).

### Start the docs locally
`docs/scripts/start-docs.sh` installs the Python dependencies (and the npm dependencies if missing), generates the
docs and starts the dev server. It works from any directory and requires uv, node and npm. Extra options are passed
on to `docusaurus start`.
```
$ docs/scripts/start-docs.sh
$ docs/scripts/start-docs.sh --no-open
```
Re-run `docs/scripts/generate-docs.sh` to pick up changes in generated pages while the server is running.

### Manual steps

To see the live development version you the docs you need to 1. install the dependencies and 2. start the development
server. This will start a web-server that you can access in the web-browser. Follow the link in your terminal.
```
$ npm install
```
```
$ npm run start
```

This command starts a local development server and opens up a browser window. Most changes are reflected live without having to restart the server.

### Build and serve locally
In order to see if the docs builds without error, you can either build with npm directly or use the Dockerfile.

For npm you run:
```
$ npm run build && npm run serve
```

This will start a web-server that you can access in the web-browser. Follow the link in your terminal.

### Generated docs
These pages are generated from the code for the current version, in CI before every docs build, and are not
committed (see `.gitignore`):

- Process, energy and YAML reference, energy units and the YAML changelog (`src/generate_yaml_asset_docs.py`)
- The NextGen example page and its downloadable zip (`src/generate_fixture.py`)
- CLI reference (`typer ... utils docs`)
- JSON schema (`src/generate_json_schema.py`)

Docs for previous versions are kept in their published builds, see [Versioning](#versioning).

Generate them locally with (requires [uv](https://docs.astral.sh/uv/) and `uv sync`, works from any directory):
```
$ docs/scripts/generate-docs.sh
```

## Updating docs

### Stuff that breaks/things to check

- Katex equations - check that equations renders _once_ (not twice, _once_)  
  
  **Problem:**  
  Katex equations are duplicated.

  **Solution:**  
  Check that the katex css linked in `docusaurus.config.ts` is updated. See docs for more info https://docusaurus.io/docs/markdown-features/math-equations and https://github.com/KaTeX/KaTeX for more up to date cdn instructions.

  **Explanation:**  
  katex creates a `span` with the css class of `katex-html`, this element 
  should be hidden by the css. That does not happen if the css isn't loaded 
  correctly or might happen if the css is outdated.

- Mermaid diagrams - check that diagrams renders correctly

- Search - check that links in search work, including anchors/subsections
  
  **Problem:**
  Search linking to anchors (`some/url#subsection) did not work
  
  **Solution:**
  Update `docusaurus-search-local`
