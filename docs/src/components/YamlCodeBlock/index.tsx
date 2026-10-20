import React from 'react';
import CodeBlock, {Props as CodeBlockProps} from '@theme/CodeBlock';
import {IndentGuidesProvider} from './IndentGuidesContext';

interface YamlCodeBlockProps extends Omit<CodeBlockProps, 'language' | 'children'> {
  children: string;
  /**
   * Spaces per indentation level.
   * - number: use this width
   * - 'auto' (default): detect from the content (greatest common divisor of the leading spaces)
   */
  indent?: number | 'auto';
}

function gcd(a: number, b: number): number {
  return b === 0 ? a : gcd(b, a % b);
}

/** Detect indentation width from content. Falls back to 2 when there is no indentation. */
export function detectIndent(code: string): number {
  let result = 0;
  for (const line of code.split('\n')) {
    if (line.trim() === '') continue;
    const leading = line.length - line.trimStart().length;
    if (leading > 0) result = gcd(result, leading);
  }
  return result || 2;
}

/**
 * YAML code block that draws vertical indent guides.
 * Uses the standard Docusaurus CodeBlock (title, copy button, themes), the guides are
 * drawn by the swizzled `CodeBlock/Line` when inside this component.
 */
export default function YamlCodeBlock({children, indent = 'auto', ...props}: YamlCodeBlockProps) {
  const width = indent === 'auto' ? detectIndent(children) : indent;
  return (
    <IndentGuidesProvider value={width}>
      <CodeBlock language="yaml" {...props}>
        {children}
      </CodeBlock>
    </IndentGuidesProvider>
  );
}
