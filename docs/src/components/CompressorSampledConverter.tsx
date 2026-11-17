import React, { useState } from 'react';

const SECONDS_PER_DAY = 86400;

type Table = string[][];

interface Conversion {
  compressor: Table;
  turbine: Table;
}

function parseCsv(text: string): Table {
  return text
    .split(/\r?\n/)
    .map((line) => line.trim())
    .filter((line) => line.length > 0 && !line.startsWith('#'))
    .map((line) => line.split(',').map((cell) => cell.trim()));
}

export function convert(csv: string, lowerHeatingValue: number): Conversion | string {
  const [headers, ...rows] = parseCsv(csv);
  if (!headers) {
    return 'Paste the content of a COMPRESSOR_SAMPLED file with POWER and FUEL columns.';
  }
  const upperHeaders = headers.map((header) => header.toUpperCase());
  const powerIndex = upperHeaders.indexOf('POWER');
  const fuelIndex = upperHeaders.indexOf('FUEL');
  if (powerIndex < 0 || fuelIndex < 0) {
    return 'The file must have both a POWER and a FUEL column.';
  }

  const keptIndices = upperHeaders.map((_, index) => index).filter((index) => index !== fuelIndex);
  const compressor = [
    keptIndices.map((index) => (index === powerIndex ? 'MECHANICAL_POWER' : headers[index])),
    ...rows.map((row) => keptIndices.map((index) => row[index] ?? '')),
  ];

  const efficiencyByPower = new Map<number, number>();
  for (const row of rows) {
    const power = Number(row[powerIndex]);
    const fuel = Number(row[fuelIndex]);
    if (power > 0 && fuel > 0) {
      efficiencyByPower.set(power, (power * SECONDS_PER_DAY) / (lowerHeatingValue * fuel));
    }
  }
  const turbine = [
    ['LOAD', 'EFFICIENCY'],
    ...[...efficiencyByPower.entries()]
      .sort(([a], [b]) => a - b)
      .map(([power, efficiency]) => [String(power), efficiency.toFixed(4)]),
  ];

  return { compressor, turbine };
}

function toCsv(table: Table): string {
  return table.map((row) => row.join(',')).join('\n') + '\n';
}

function TableWithCopy({ title, table }: { title: string; table: Table }) {
  const [copied, setCopied] = useState(false);
  const [headers, ...rows] = table;

  const copy = async () => {
    await navigator.clipboard.writeText(toCsv(table));
    setCopied(true);
    setTimeout(() => setCopied(false), 1500);
  };

  return (
    <div className="margin-bottom--lg">
      <div className="margin-bottom--sm">
        <strong>{title}</strong>{' '}
        <button type="button" className="button button--sm button--secondary" onClick={copy}>
          {copied ? 'Copied' : 'Copy as CSV'}
        </button>
      </div>
      <table>
        <thead>
          <tr>
            {headers.map((header, index) => (
              <th key={index}>{header}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((row, rowIndex) => (
            <tr key={rowIndex}>
              {row.map((cell, cellIndex) => (
                <td key={cellIndex}>{cell}</td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export default function CompressorSampledConverter() {
  const [csv, setCsv] = useState('');
  const [lowerHeatingValue, setLowerHeatingValue] = useState(38.0);

  const result = csv.trim().length > 0 ? convert(csv, lowerHeatingValue) : null;

  return (
    <div className="margin-vert--md">
      <label className="margin-bottom--sm" style={{ display: 'block' }}>
        <strong>Old FILE content</strong>
        <textarea
          value={csv}
          onChange={(event) => setCsv(event.target.value)}
          placeholder={'RATE, SUCTION_PRESSURE, DISCHARGE_PRESSURE, POWER, FUEL\n1000000, 15, 100, 3.23, 31974'}
          rows={10}
          style={{ width: '100%', fontFamily: 'var(--ifm-font-family-monospace)' }}
        />
      </label>
      <label className="margin-bottom--md" style={{ display: 'block' }}>
        <strong>LOWER_HEATING_VALUE</strong> [MJ/Sm³]{' '}
        <input
          type="number"
          step="any"
          min="0"
          value={lowerHeatingValue}
          onChange={(event) => setLowerHeatingValue(Number(event.target.value))}
        />
      </label>
      {typeof result === 'string' && <div className="alert alert--warning">{result}</div>}
      {result !== null && typeof result !== 'string' && (
        <>
          <TableWithCopy title="Compressor FILE" table={result.compressor} />
          <TableWithCopy title="Gas turbine CURVE" table={result.turbine} />
        </>
      )}
    </div>
  );
}
