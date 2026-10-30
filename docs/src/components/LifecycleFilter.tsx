import React, { useEffect, useRef, useState } from 'react';

interface ToggleConfig {
  key: string;
  label: string;
  matches: (badgeKinds: Set<string>) => boolean;
}

const HEADING_SELECTOR = 'h2, h3, h4, h5, h6';
const BADGE_SELECTOR = '.lifecycle-badge';
const HIDDEN_CLASS = 'lifecycle-hidden';
const ALL_VERSIONS = 'all';
const VERSIONS = ['1', '2', '3'];

const TOGGLES: ToggleConfig[] = [
  {
    key: 'hideDeprecated',
    label: 'Hide deprecated',
    matches: (kinds) => kinds.has('deprecated'),
  },
  {
    key: 'hideRemoved',
    label: 'Hide removed',
    matches: (kinds) => kinds.has('removed'),
  },
  {
    key: 'onlyIntroduced',
    label: 'Only show new elements',
    matches: (kinds) => !kinds.has('introduced'),
  },
];

interface SectionLifecycle {
  level: number;
  introduced: boolean;
  availableSince: number;
  removedSince: number | null;
}

function badgeKindsOf(container: Element): Set<string> {
  const kinds = new Set<string>();
  container.querySelectorAll(BADGE_SELECTOR).forEach((badge) => {
    Array.from(badge.classList).forEach((className) => {
      const match = /^lifecycle-badge--(.+)$/.exec(className);
      if (match) {
        kinds.add(match[1]);
      }
    });
  });
  return kinds;
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

function shouldHide(
  active: Record<string, boolean>,
  kinds: Set<string>,
): boolean {
  return TOGGLES.some((toggle) => active[toggle.key] && toggle.matches(kinds));
}

function applyFilters(active: Record<string, boolean>, version: string) {
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

  const anyToggleActive = TOGGLES.some((toggle) => active[toggle.key]);
  const versionFilterActive = version !== ALL_VERSIONS;

  if (anyToggleActive || versionFilterActive) {
    // Headings own their whole section (heading + following siblings until the next
    // heading of equal or shallower level). Lifecycle is inherited from the nearest
    // ancestor heading, so fields nested under e.g. a v2-new section aren't wrongly
    // shown/hidden just because they don't carry their own badge.
    const stack: SectionLifecycle[] = [];
    content
      .querySelectorAll<HTMLElement>(`${HEADING_SELECTOR}, tr`)
      .forEach((element) => {
        const parent =
          element.tagName === 'TR' ? stack[stack.length - 1] : undefined;
        const isHeading = element.tagName !== 'TR';

        const kinds = badgeKindsOf(element);
        const { introducedIn, removedIn } = badgeVersionsOf(element);

        let ancestor: SectionLifecycle | undefined = parent;
        if (isHeading) {
          const level = headingLevel(element);
          while (stack.length > 0 && stack[stack.length - 1].level >= level) {
            stack.pop();
          }
          ancestor = stack[stack.length - 1];
        }

        const introduced =
          kinds.has('introduced') || (ancestor?.introduced ?? false);
        const availableSince = introducedIn ?? ancestor?.availableSince ?? 1;
        const removedSince = removedIn ?? ancestor?.removedSince ?? null;

        if (isHeading) {
          stack.push({
            level: headingLevel(element),
            introduced,
            availableSince,
            removedSince,
          });
        }

        const effectiveKinds = introduced
          ? new Set([...kinds, 'introduced'])
          : kinds;
        const hideByToggle =
          anyToggleActive && shouldHide(active, effectiveKinds);
        const hideByVersion =
          versionFilterActive &&
          !isAvailableForVersion(availableSince, removedSince, version);
        if (!hideByToggle && !hideByVersion) {
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
 * Toolbar that toggles visibility of headings/sections and table rows marked
 * with a `<LifecycleBadge>` (see generate_yaml_asset_docs.py), and keeps the
 * table-of-contents sidebar in sync with whatever ends up hidden.
 */
export default function LifecycleFilter() {
  const [active, setActive] = useState<Record<string, boolean>>({});
  const [version, setVersion] = useState<string>(ALL_VERSIONS);
  const filterStateRef = useRef({ active, version });
  filterStateRef.current = { active, version };

  useEffect(() => {
    applyFilters(active, version);
  }, [active, version]);

  useEffect(() => {
    // The table of contents can re-render after navigation/highlighting;
    // keep it in sync whenever that happens. Reads the latest filter state via
    // a ref so this observer doesn't need to be re-subscribed on every change.
    const observer = new MutationObserver(() => {
      const { active: currentActive, version: currentVersion } =
        filterStateRef.current;
      applyFilters(currentActive, currentVersion);
    });
    const toc = document.querySelector('.table-of-contents')?.parentElement;
    if (toc) {
      observer.observe(toc, { childList: true, subtree: true });
    }
    return () => observer.disconnect();
  }, []);

  useEffect(() => {
    return () => applyFilters({}, ALL_VERSIONS);
  }, []);

  function toggle(key: string) {
    setActive((prev) => ({ ...prev, [key]: !prev[key] }));
  }

  return (
    <div className="lifecycle-filter">
      {TOGGLES.map((t) => (
        <label key={t.key} className="lifecycle-filter__option">
          <input
            type="checkbox"
            checked={Boolean(active[t.key])}
            onChange={() => toggle(t.key)}
          />
          {t.label}
        </label>
      ))}
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
