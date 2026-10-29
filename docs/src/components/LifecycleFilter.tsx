import React, { useEffect, useState } from 'react';

interface ToggleConfig {
  key: string;
  label: string;
  htmlClass: string;
}

const TOGGLES: ToggleConfig[] = [
  {
    key: 'hideDeprecated',
    label: 'Hide deprecated',
    htmlClass: 'ecalc-hide-deprecated',
  },
  {
    key: 'hideRemoved',
    label: 'Hide removed',
    htmlClass: 'ecalc-hide-removed',
  },
  {
    key: 'onlyIntroduced',
    label: 'Only show new elements',
    htmlClass: 'ecalc-only-introduced',
  },
];

/**
 * Toolbar that toggles visibility of elements marked with `data-lifecycle-*`
 * attributes (see LifecycleBadge and the `<div data-lifecycle-section ...>`
 * wrappers emitted by generate_yaml_asset_docs.py), by adding/removing a
 * class on the document root. The matching CSS rules live in custom.css.
 */
export default function LifecycleFilter() {
  const [active, setActive] = useState<Record<string, boolean>>({});

  useEffect(() => {
    const root = document.documentElement;
    for (const toggle of TOGGLES) {
      root.classList.toggle(toggle.htmlClass, Boolean(active[toggle.key]));
    }
  }, [active]);

  useEffect(() => {
    return () => {
      const root = document.documentElement;
      for (const toggle of TOGGLES) {
        root.classList.remove(toggle.htmlClass);
      }
    };
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
    </div>
  );
}
