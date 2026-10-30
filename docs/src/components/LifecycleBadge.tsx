import React from 'react';

type LifecycleKind = 'introduced' | 'deprecated' | 'removed';

interface LifecycleBadgeProps {
  kind: LifecycleKind;
  version: number | string;
}

const LABELS: Record<LifecycleKind, string> = {
  introduced: 'New in v',
  deprecated: 'Deprecated in v',
  removed: 'Removed in v',
};

export default function LifecycleBadge({ kind, version }: LifecycleBadgeProps) {
  return (
    <span className={`lifecycle-badge lifecycle-badge--${kind}`}>
      {LABELS[kind]}
      {version}
    </span>
  );
}
