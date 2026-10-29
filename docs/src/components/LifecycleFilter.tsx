import React, { useEffect, useState } from 'react';

interface ToggleConfig {
  key: string;
  label: string;
  matches: (badgeKinds: Set<string>) => boolean;
}

const HEADING_SELECTOR = 'h2, h3, h4, h5, h6';
const BADGE_SELECTOR = '.lifecycle-badge';
const HIDDEN_CLASS = 'lifecycle-hidden';

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
  while (sibling && !(sibling.matches(HEADING_SELECTOR) && headingLevel(sibling) <= level)) {
    elements.push(sibling);
    sibling = sibling.nextElementSibling;
  }
  return elements;
}

function shouldHide(active: Record<string, boolean>, kinds: Set<string>): boolean {
  return TOGGLES.some((toggle) => active[toggle.key] && toggle.matches(kinds));
}

function applyFilters(active: Record<string, boolean>) {
  const content = document.querySelector<HTMLElement>('article .markdown') ?? document.querySelector('article');
  if (!content) {
    return;
  }

  // Reset.
  content.querySelectorAll(`.${HIDDEN_CLASS}`).forEach((el) => el.classList.remove(HIDDEN_CLASS));

  const anyActive = TOGGLES.some((toggle) => active[toggle.key]);
  if (anyActive) {
    // Headings own their whole section (heading + following siblings until the next
    // heading of equal or shallower level). "introduced" is inherited from the nearest
    // ancestor heading, so fields nested under a v2-new section aren't wrongly hidden
    // by "only show new elements" just because they don't carry their own badge.
    const introducedStack: { level: number; introduced: boolean }[] = [];
    content.querySelectorAll<HTMLElement>(HEADING_SELECTOR).forEach((heading) => {
      const level = headingLevel(heading);
      while (introducedStack.length > 0 && introducedStack[introducedStack.length - 1].level >= level) {
        introducedStack.pop();
      }
      const kinds = badgeKindsOf(heading);
      const inheritedIntroduced = introducedStack[introducedStack.length - 1]?.introduced ?? false;
      const introduced = kinds.has('introduced') || inheritedIntroduced;
      introducedStack.push({ level, introduced });

      const effectiveKinds = introduced ? new Set([...kinds, 'introduced']) : kinds;
      if (shouldHide(active, effectiveKinds)) {
        collectSection(heading).forEach((el) => el.classList.add(HIDDEN_CLASS));
      }
    });

    // Individual table rows for leaf fields (not their own heading/section).
    content.querySelectorAll<HTMLElement>('tr').forEach((row) => {
      if (row.classList.contains(HIDDEN_CLASS)) {
        return;
      }
      const kinds = badgeKindsOf(row);
      if (shouldHide(active, kinds)) {
        row.classList.add(HIDDEN_CLASS);
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
  document.querySelectorAll<HTMLAnchorElement>('.table-of-contents a[href*="#"]').forEach((link) => {
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

  useEffect(() => {
    applyFilters(active);
  }, [active]);

  useEffect(() => {
    // The table of contents can re-render after navigation/highlighting;
    // keep it in sync whenever that happens.
    const observer = new MutationObserver(() => applyFilters(active));
    const toc = document.querySelector('.table-of-contents')?.parentElement;
    if (toc) {
      observer.observe(toc, { childList: true, subtree: true });
    }
    return () => observer.disconnect();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    return () => applyFilters({});
  }, []);

  function toggle(key: string) {
    setActive((prev) => ({ ...prev, [key]: !prev[key] }));
  }

  return (
    <div className="lifecycle-filter">
      {TOGGLES.map((t) => (
        <label key={t.key} className="lifecycle-filter__option">
          <input type="checkbox" checked={Boolean(active[t.key])} onChange={() => toggle(t.key)} />
          {t.label}
        </label>
      ))}
    </div>
  );
}
