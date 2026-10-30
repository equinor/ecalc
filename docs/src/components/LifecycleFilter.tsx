import React, { useEffect, useRef, useState } from 'react';

const HEADING_SELECTOR = 'h2, h3, h4, h5, h6';
const BADGE_SELECTOR = '.lifecycle-badge';
const HIDDEN_CLASS = 'lifecycle-hidden';
const ALL_VERSIONS = 'all';
const VERSIONS = ['1', '2', '3'];

interface SectionLifecycle {
  level: number;
  availableSince: number;
  removedSince: number | null;
}

/** Read a container's own introduced/removed versions from its <LifecycleBadge> `data-version`s. */
function badgeVersionsOf(container: Element): {
  introducedIn?: number;
  removedIn?: number;
} {
  let introducedIn: number | undefined;
  let removedIn: number | undefined;
  container.querySelectorAll<HTMLElement>(BADGE_SELECTOR).forEach((badge) => {
    const version = Number(badge.dataset.version);
    if (Number.isNaN(version)) {
      return;
    }
    if (badge.classList.contains('lifecycle-badge--introduced')) {
      introducedIn = version;
    }
    if (badge.classList.contains('lifecycle-badge--removed')) {
      removedIn = version;
    }
  });
  return { introducedIn, removedIn };
}

function isAvailableForVersion(
  availableSince: number,
  removedSince: number | null,
  version: string,
): boolean {
  const selected = Number(version);
  if (selected < availableSince) {
    return false;
  }
  return !(removedSince !== null && selected >= removedSince);
}

function headingLevel(heading: Element): number {
  return Number(heading.tagName.slice(1));
}

/**
 * Collect a heading and every following sibling up to (but not including)
 * the next heading of equal or shallower level — i.e. everything that
 * belongs to that heading's section.
 */
function collectSection(heading: Element): Element[] {
  const elements: Element[] = [heading];
  const level = headingLevel(heading);
  let sibling = heading.nextElementSibling;
  while (
    sibling &&
    !(sibling.matches(HEADING_SELECTOR) && headingLevel(sibling) <= level)
  ) {
    elements.push(sibling);
    sibling = sibling.nextElementSibling;
  }
  return elements;
}

function applyFilters(version: string) {
  const content =
    document.querySelector<HTMLElement>('article .markdown') ??
    document.querySelector('article');
  if (!content) {
    return;
  }

  // Reset.
  content.querySelectorAll(`.${HIDDEN_CLASS}`).forEach((el) => {
    el.classList.remove(HIDDEN_CLASS);
  });

  if (version !== ALL_VERSIONS) {
    // Headings own their whole section (heading + following siblings until the next
    // heading of equal or shallower level). Lifecycle is inherited from the nearest
    // ancestor heading, so fields nested under e.g. a v2-new section aren't wrongly
    // shown/hidden just because they don't carry their own badge.
    const stack: SectionLifecycle[] = [];
    content
      .querySelectorAll<HTMLElement>(`${HEADING_SELECTOR}, tr`)
      .forEach((element) => {
        const isHeading = element.tagName !== 'TR';
        const parent = isHeading ? undefined : stack[stack.length - 1];

        const { introducedIn, removedIn } = badgeVersionsOf(element);

        let ancestor: SectionLifecycle | undefined = parent;
        if (isHeading) {
          const level = headingLevel(element);
          while (stack.length > 0 && stack[stack.length - 1].level >= level) {
            stack.pop();
          }
          ancestor = stack[stack.length - 1];
        }

        const availableSince = introducedIn ?? ancestor?.availableSince ?? 1;
        const removedSince = removedIn ?? ancestor?.removedSince ?? null;

        if (isHeading) {
          stack.push({
            level: headingLevel(element),
            availableSince,
            removedSince,
          });
        }

        if (isAvailableForVersion(availableSince, removedSince, version)) {
          return;
        }

        if (isHeading) {
          collectSection(element).forEach((el) => {
            el.classList.add(HIDDEN_CLASS);
          });
        } else {
          element.classList.add(HIDDEN_CLASS);
        }
      });
  }

  syncTableOfContents(content);
}

/**
 * Hide table-of-contents entries (desktop and mobile) whose target heading
 * was hidden by applyFilters, and restore the rest.
 */
function syncTableOfContents(content: Element) {
  document
    .querySelectorAll<HTMLAnchorElement>('.table-of-contents a[href*="#"]')
    .forEach((link) => {
      const hash = link.hash || link.getAttribute('href') || '';
      const id = hash.startsWith('#') ? hash.slice(1) : hash;
      const item = link.closest('li') ?? link;
      if (!id) {
        item.classList.remove(HIDDEN_CLASS);
        return;
      }

      const target = content.querySelector(`#${CSS.escape(id)}`);
      if (target?.classList.contains(HIDDEN_CLASS)) {
        item.classList.add(HIDDEN_CLASS);
      } else {
        item.classList.remove(HIDDEN_CLASS);
      }
    });
}

/**
 * Toolbar that filters visibility of headings/sections and table rows marked
 * with a `<LifecycleBadge>` (see generate_yaml_asset_docs.py) down to a single
 * chosen YAML_VERSION, and keeps the table-of-contents sidebar in sync with
 * whatever ends up hidden.
 */
export default function LifecycleFilter() {
  const [version, setVersion] = useState<string>(ALL_VERSIONS);
  const versionRef = useRef(version);
  versionRef.current = version;

  useEffect(() => {
    applyFilters(version);
  }, [version]);

  useEffect(() => {
    // The table of contents can re-render after navigation/highlighting;
    // keep it in sync whenever that happens. Reads the latest filter state via
    // a ref so this observer doesn't need to be re-subscribed on every change.
    const observer = new MutationObserver(() => {
      applyFilters(versionRef.current);
    });
    const toc = document.querySelector('.table-of-contents')?.parentElement;
    if (toc) {
      observer.observe(toc, { childList: true, subtree: true });
    }
    return () => observer.disconnect();
  }, []);

  useEffect(() => {
    return () => applyFilters(ALL_VERSIONS);
  }, []);

  return (
    <div className="lifecycle-filter">
      <div
        className="lifecycle-filter__versions"
        role="radiogroup"
        aria-label="Filter by YAML version"
      >
        <span className="lifecycle-filter__versions-label">
          Show elements available in:
        </span>
        <label className="lifecycle-filter__option">
          <input
            type="radio"
            name="lifecycle-filter-version"
            checked={version === ALL_VERSIONS}
            onChange={() => setVersion(ALL_VERSIONS)}
          />
          All versions
        </label>
        {VERSIONS.map((v) => (
          <label key={v} className="lifecycle-filter__option">
            <input
              type="radio"
              name="lifecycle-filter-version"
              checked={version === v}
              onChange={() => setVersion(v)}
            />
            YAML_VERSION {v}
          </label>
        ))}
      </div>
    </div>
  );
}
