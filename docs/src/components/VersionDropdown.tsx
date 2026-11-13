import React from 'react';
import DropdownNavbarItem from '@theme/NavbarItem/DropdownNavbarItem';
import type { Props as DropdownNavbarItemProps } from '@theme/NavbarItem/DropdownNavbarItem';
import { NEXT_VERSION, VERSION_ROOT_ATTRIBUTE, useDocsVersions } from '@site/src/utils/docsVersions';

type Props = Omit<DropdownNavbarItemProps, 'items' | 'label'>;

export default function VersionDropdown(props: Props): React.ReactNode {
  const info = useDocsVersions();
  if (!info) {
    return null;
  }
  const { current, manifest, pathFor } = info;
  const activeClassName = props.mobile ? 'menu__link--active' : 'dropdown__link--active';

  const link = (label: string, versionBaseUrl: string, isCurrent: boolean) => ({
    label,
    href: pathFor(versionBaseUrl),
    autoAddBaseUrl: false,
    className: isCurrent ? activeClassName : undefined,
    [VERSION_ROOT_ATTRIBUTE]: versionBaseUrl,
  });

  const items = manifest.versions.map((version) =>
    link(version.name === manifest.latest ? `${version.name} (latest)` : version.name, version.path, version.name === current),
  );
  if (manifest.next) {
    items.push(link('Next (unreleased)', manifest.next, current === NEXT_VERSION));
  }

  return <DropdownNavbarItem {...props} label={current === NEXT_VERSION ? 'Next' : current} items={items} />;
}
