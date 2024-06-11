# Get started

This website is built using [Docusaurus 3](https://docusaurus.io/), a modern static website generator.

In order to edit the docs you need either [NodeJS (recommended)](https://nodejs.org/en/download/) together with
the package manager [npm]. See [local development](#local-development) for details on how to get started with local development.

In case you don't have a developer environment in NodeJS, or it is not possible to set up. Then the backup solution
is to host the docs locally during development using a similar Python framework called [MKDocs](https://www.mkdocs.org/), please
find the [Python alternative](#python-alternative) section further down.

Note! Currently [Chrome does not support visualizing LaTeX/KaTeX](https://developer.mozilla.org/en-US/docs/Web/MathML/Element/semantics#browser_compatibility)
The feature is in experimental stage in Chrome 107, and will be fully supported at release 109. This release is due sometime
around late 2022. Use #enable-experimental-web-platform-features in chrome://flags for support until 109 is released.

## How it works

The Doc navigation is dynamically generated based on the file structure under ./docs. This is where you would normally
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
ending will be .mdx. Note that this will not be rendered in the Python setup.

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

The docs are versioned. This does not include the blog/release notes and other pages that are not part of the docs
structure. The versioning works by creating a snapshot of the current documents under /docs, and puts them under
/versioned_docs and /versioned_sidebars.

Please see the official [versioning docs](https://docusaurus.io/docs/versioning) for details.

Note the dropdown menu at the right top menu where you can select other versions than the latest. Note that the
unreleased version (main) is named "Next". This may change in the future. The latest published version is the
default version that the user will see when entering the docs.

### Blog / Release notes

The blog functionality is currently used for release notes, and is named this on the top menu bar. This is a
business-related release note that should also link to migration guides and GitHub release notes.

## Local development

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

### Generate API reference documentation
In order to generate the API reference documentation while also building the docs, use the following:
```
$ npm run build
$ poetry run python make-api-reference.py
$ npm run serve
```

### Generate CLI reference documentation
In order to generate the CLI reference documentation, use the following (from `src`):
```
$ cd src
$ poetry run python generate_docs.py > ../docs/docs/about/references/cli_reference.md
```

Then build the documentation:
```
$ npm run build && npm run serve
```

## Python alternative
To avoid dependency on NodeJS and npm for some users, we have made it possible to edit/view the docs using python:

```
$ poetry install
```

```
$ mkdocs serve
```

This will open a browser.

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