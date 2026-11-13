#!/usr/bin/env node
// Updates a checkout of the gh-pages branch with a new docs build, and maintains versions.json.
//
// Layout of the gh-pages branch:
//   /index.html      redirect to the latest release (docs/static-root, published from main)
//   /404.html        same redirect, handles all missing paths such as old links to /docs/...
//   /vX.Y/           the newest minor releases, patches overwrite their minor (built with baseUrl = siteRoot + 'vX.Y/')
//   /next/           unreleased docs from main (built with baseUrl = siteRoot + 'next/')
//   /versions.json   read at runtime by the redirect, the version dropdown and the banner
//
// Usage:
//   node deploy-versioned-docs.mjs --site <gh-pages dir> --channel next --build <dir> --root <static-root dir>
//   node deploy-versioned-docs.mjs --site <gh-pages dir> --channel release --version vX.Y.Z --build <dir>

import { cpSync, existsSync, mkdirSync, readdirSync, readFileSync, rmSync, writeFileSync } from 'node:fs';
import { join, resolve } from 'node:path';
import { pathToFileURL } from 'node:url';
import { parseArgs } from 'node:util';

export const NEXT_FOLDER = 'next';
export const MANIFEST_FILE = 'versions.json';
const VERSION_FOLDER_PATTERN = /^v\d+\.\d+$/;
const PRESERVED_ROOT_ENTRIES = new Set(['.git', '.nojekyll', MANIFEST_FILE, NEXT_FOLDER]);

export function parseRelease(release) {
  const match = /^v?(\d+)\.(\d+)\.(\d+)$/.exec(release);
  if (!match) {
    throw new Error(`Invalid release version '${release}', expected vX.Y.Z`);
  }
  const [major, minor, patch] = match.slice(1).map(Number);
  return { major, minor, patch, tag: `v${major}.${minor}.${patch}`, name: `v${major}.${minor}` };
}

function compareReleases(a, b) {
  const x = parseRelease(a);
  const y = parseRelease(b);
  return x.major - y.major || x.minor - y.minor || x.patch - y.patch;
}

export function emptyManifest() {
  return { latest: undefined, next: undefined, versions: [] };
}

/**
 * Adds a release to the manifest. Returns the new manifest and what should happen on disk.
 * The manifest passed in is not modified.
 */
export function addRelease(manifest, release, { keep, siteRoot }) {
  const { tag, name } = parseRelease(release);
  const existing = manifest.versions.find((version) => version.name === name);
  if (existing && compareReleases(existing.release, tag) > 0) {
    return { deploy: false, reason: `${name} already has the newer release ${existing.release}`, manifest };
  }

  const entry = { name, release: tag, path: `${siteRoot}${name}/` };
  const all = [...manifest.versions.filter((version) => version.name !== name), entry].sort((a, b) =>
    compareReleases(b.release, a.release),
  );
  const versions = all.slice(0, keep);
  if (!versions.includes(entry)) {
    return { deploy: false, reason: `${name} is older than the ${keep} versions that are kept`, manifest };
  }

  return {
    deploy: true,
    name,
    manifest: { ...manifest, latest: versions[0].name, versions },
  };
}

export function readManifest(site) {
  const file = join(site, MANIFEST_FILE);
  if (!existsSync(file)) {
    return emptyManifest();
  }
  return { ...emptyManifest(), ...JSON.parse(readFileSync(file, 'utf8')) };
}

function writeManifest(site, manifest) {
  writeFileSync(join(site, MANIFEST_FILE), `${JSON.stringify(manifest, null, 2)}\n`);
}

function replaceFolder(site, folder, build) {
  const target = join(site, folder);
  rmSync(target, { recursive: true, force: true });
  cpSync(build, target, { recursive: true });
}

function replaceRoot(site, root, siteRoot) {
  for (const entry of readdirSync(site)) {
    if (!PRESERVED_ROOT_ENTRIES.has(entry) && !VERSION_FOLDER_PATTERN.test(entry)) {
      rmSync(join(site, entry), { recursive: true, force: true });
    }
  }
  cpSync(root, site, { recursive: true });
  const redirect = readFileSync(join(root, 'index.html'), 'utf8').replaceAll('__SITE_ROOT__', siteRoot);
  writeFileSync(join(site, 'index.html'), redirect);
  writeFileSync(join(site, '404.html'), redirect);
}

function pruneVersionFolders(site, manifest) {
  const kept = new Set(manifest.versions.map((version) => version.name));
  const pruned = readdirSync(site).filter((entry) => VERSION_FOLDER_PATTERN.test(entry) && !kept.has(entry));
  for (const entry of pruned) {
    rmSync(join(site, entry), { recursive: true, force: true });
  }
  return pruned;
}

export function deploy({ site, channel, version, build, root, keep = 5, siteRoot = '/ecalc/' }) {
  if (!existsSync(build)) {
    throw new Error(`Build folder '${build}' does not exist`);
  }
  mkdirSync(site, { recursive: true });
  const manifest = readManifest(site);

  if (channel === 'next') {
    if (!root || !existsSync(join(root, 'index.html'))) {
      throw new Error(`Root folder '${root}' with index.html does not exist`);
    }
    replaceFolder(site, NEXT_FOLDER, build);
    replaceRoot(site, root, siteRoot);
    writeManifest(site, { ...manifest, next: `${siteRoot}${NEXT_FOLDER}/` });
    writeFileSync(join(site, '.nojekyll'), '');
    return { deployed: [NEXT_FOLDER, '/'], pruned: [] };
  }

  if (channel !== 'release') {
    throw new Error(`Unknown channel '${channel}', expected 'next' or 'release'`);
  }
  const result = addRelease(manifest, version, { keep, siteRoot });
  if (!result.deploy) {
    return { deployed: [], pruned: [], skipped: result.reason };
  }

  replaceFolder(site, result.name, build);
  const pruned = pruneVersionFolders(site, result.manifest);
  writeManifest(site, result.manifest);
  writeFileSync(join(site, '.nojekyll'), '');
  return { deployed: [result.name], pruned };
}

function main() {
  const { values } = parseArgs({
    options: {
      site: { type: 'string' },
      channel: { type: 'string' },
      version: { type: 'string' },
      build: { type: 'string' },
      root: { type: 'string' },
      keep: { type: 'string', default: '5' },
      'site-root': { type: 'string', default: '/ecalc/' },
    },
  });
  for (const required of ['site', 'channel', 'build']) {
    if (!values[required]) {
      throw new Error(`Missing --${required}`);
    }
  }
  if (values.channel === 'next' && !values.root) {
    throw new Error('Missing --root for the next channel');
  }
  if (values.channel === 'release' && !values.version) {
    throw new Error('Missing --version for the release channel');
  }
  const result = deploy({
    site: resolve(values.site),
    channel: values.channel,
    version: values.version,
    build: resolve(values.build),
    root: values.root && resolve(values.root),
    keep: Number(values.keep),
    siteRoot: values['site-root'],
  });
  console.log(JSON.stringify(result, null, 2));
}

if (import.meta.url === pathToFileURL(process.argv[1]).href) {
  main();
}
