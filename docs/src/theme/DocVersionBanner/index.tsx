import React from 'react';
import clsx from 'clsx';
import { ThemeClassNames } from '@docusaurus/theme-common';
import type { Props } from '@theme/DocVersionBanner';
import { NEXT_VERSION, VERSION_ROOT_ATTRIBUTE, useDocsVersions } from '@site/src/utils/docsVersions';

/**
 * Replaces the Docusaurus version banner, which only knows about versions inside a single build.
 * Whether this build is outdated is decided at runtime from versions.json.
 */
export default function DocVersionBanner({ className }: Props): React.ReactNode {
  const info = useDocsVersions();
  if (!info || !info.latestPath || info.current === info.manifest.latest) {
    return null;
  }
  const { current, latestPath, manifest, pathFor } = info;
  const isNext = current === NEXT_VERSION;
  const latestLink = (
    <a href={pathFor(latestPath)} {...{ [VERSION_ROOT_ATTRIBUTE]: latestPath }}>
      latest version ({manifest.latest})
    </a>
  );

  return (
    <div
      className={clsx(
        className,
        ThemeClassNames.docs.docVersionBanner,
        'alert margin-bottom--md',
        isNext ? 'alert--info' : 'alert--warning',
      )}
      role="alert"
    >
      {isNext ? (
        <>
          This is unreleased documentation built from the main branch. For the released documentation, see
          the <b>{latestLink}</b>.
        </>
      ) : (
        <>
          This is documentation for eCalc™ <b>{current}</b>, which is not the latest version. For up-to-date
          documentation, see the <b>{latestLink}</b>.
        </>
      )}
    </div>
  );
}
