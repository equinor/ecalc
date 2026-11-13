import { useEffect, useState } from 'react';
import useDocusaurusContext from '@docusaurus/useDocusaurusContext';
import { useLocation } from '@docusaurus/router';

/**
 * Runtime support for the multi-version docs published to GitHub Pages.
 *
 * Every version is a separate Docusaurus build, so the list of versions cannot be known at build time.
 * Instead, each build fetches `<siteRoot>versions.json` (written by scripts/deploy-versioned-docs.mjs)
 * in the browser. That way old builds always show the current list of versions and the correct banner.
 */

export type DocsVersionEntry = {
  name: string;
  release: string;
  path: string;
};

export type DocsVersionsManifest = {
  latest?: string;
  next?: string;
  versions: DocsVersionEntry[];
};

export type DocsVersionsInfo = {
  current: string;
  latestPath?: string;
  manifest: DocsVersionsManifest;
  pathFor: (versionBaseUrl: string) => string;
};

export const NEXT_VERSION = 'next';
export const VERSION_ROOT_ATTRIBUTE = 'data-docs-version-root';

let manifestPromise: Promise<DocsVersionsManifest | null> | undefined;

function loadManifest(url: string): Promise<DocsVersionsManifest | null> {
  manifestPromise ??= fetch(url, { cache: 'no-cache' })
    .then((response) => (response.ok ? response.json() : null))
    .then((manifest) => (manifest && Array.isArray(manifest.versions) ? manifest : null))
    .catch(() => null);
  return manifestPromise;
}

function manifestVersionRoots(siteRoot: string, manifest: DocsVersionsManifest): string[] {
  const roots = manifest.versions.map((version) => version.path);
  if (manifest.next) {
    roots.push(manifest.next);
  }
  return roots.filter((root) => root.startsWith(siteRoot));
}

function sameOriginUrl(path: string): string | null {
  const url = new URL(path, window.location.origin);
  return url.origin === window.location.origin ? url.href : null;
}

let clickHandlerInstalled = false;
let allowedVersionRoots: string[] = [];
let currentBaseUrl = '/';

/**
 * Links to other versions point to separate builds, so they must be full page loads and not client side navigation.
 * The same page might not exist in the other version, so we check first and fall back to the root of that version.
 * Modified clicks (new tab etc.) are left to the browser.
 *
 * The navigation target is never taken from the DOM: the clicked link only selects one of the version roots from
 * versions.json, and the target is rebuilt from that root and the current page.
 */
function installVersionLinkClickHandler() {
  if (clickHandlerInstalled) {
    return;
  }
  clickHandlerInstalled = true;
  document.addEventListener(
    'click',
    (event) => {
      if (event.defaultPrevented || event.button !== 0 || event.metaKey || event.ctrlKey || event.shiftKey || event.altKey) {
        return;
      }
      const anchor = (event.target as Element | null)?.closest?.(`a[${VERSION_ROOT_ATTRIBUTE}]`);
      const selectedRoot = anchor?.getAttribute(VERSION_ROOT_ATTRIBUTE);
      const versionRoot = allowedVersionRoots.find((root) => root === selectedRoot);
      if (!versionRoot) {
        return;
      }
      const { pathname } = window.location;
      const pagePath = pathname.startsWith(currentBaseUrl) ? pathname.slice(currentBaseUrl.length) : '';
      const pageUrl = sameOriginUrl(`${versionRoot}${pagePath}`);
      const rootUrl = sameOriginUrl(versionRoot);
      if (!pageUrl || !rootUrl) {
        return;
      }
      event.preventDefault();
      event.stopPropagation();
      fetch(pageUrl, { method: 'HEAD' })
        .then((response) => (response.ok ? pageUrl : rootUrl))
        .catch(() => pageUrl)
        .then((target) => window.location.assign(target));
    },
    true,
  );
}

export function useDocsVersions(): DocsVersionsInfo | null {
  const { siteConfig } = useDocusaurusContext();
  const { pathname } = useLocation();
  const current = siteConfig.customFields?.docsVersion as string | undefined;
  const siteRoot = siteConfig.customFields?.docsSiteRoot as string | undefined;
  const [manifest, setManifest] = useState<DocsVersionsManifest | null>(null);

  useEffect(() => {
    if (!current || !siteRoot || current === 'local') {
      return;
    }
    let active = true;
    loadManifest(`${siteRoot}versions.json`).then((loaded) => {
      if (active) {
        setManifest(loaded);
        if (loaded) {
          allowedVersionRoots = manifestVersionRoots(siteRoot, loaded);
          currentBaseUrl = siteConfig.baseUrl;
          installVersionLinkClickHandler();
        }
      }
    });
    return () => {
      active = false;
    };
  }, [current, siteRoot, siteConfig.baseUrl]);

  if (!manifest || !current || !siteRoot) {
    return null;
  }

  const pagePath = pathname.startsWith(siteConfig.baseUrl) ? pathname.slice(siteConfig.baseUrl.length) : '';
  return {
    current,
    latestPath: manifest.versions.find((version) => version.name === manifest.latest)?.path,
    manifest,
    pathFor: (versionBaseUrl: string) => `${versionBaseUrl}${pagePath}`,
  };
}
