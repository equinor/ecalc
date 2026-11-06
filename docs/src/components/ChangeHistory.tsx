import React, { useState } from 'react';

interface Change {
  version: number | string;
  description: string;
}

interface ChangeHistoryProps {
  changes: Change[];
}

export default function ChangeHistory({ changes }: ChangeHistoryProps) {
  const [expanded, setExpanded] = useState(false);

  if (!changes || changes.length === 0) {
    return null;
  }

  const versions = changes.map((change) => change.version).join(', ');

  return (
    <span className="change-history">
      <button
        type="button"
        className="change-history__toggle"
        aria-expanded={expanded}
        onClick={() => setExpanded(!expanded)}
      >
        Changed in: {versions}
      </button>
      {expanded && (
        <ul className="change-history__list">
          {changes.map((change, index) => (
            <li key={index}>
              <strong>v{change.version}:</strong> {change.description}
            </li>
          ))}
        </ul>
      )}
    </span>
  );
}

