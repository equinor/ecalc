import React, {type ReactNode} from 'react';
import OriginalLine from '@theme-original/CodeBlock/Line';
import type {Props} from '@theme/CodeBlock/Line';
import {useIndentGuides} from '@site/src/components/YamlCodeBlock/IndentGuidesContext';

const INDENT_TYPE = 'indent-guide';

type Token = Props['line'][number];

/**
 * Wraps the original line. Only when rendered inside <YamlCodeBlock> (context set) is the
 * leading whitespace split into one token per indentation level, each drawn with a guide on
 * its left edge. The tokens consist of the actual space characters, so guides line up exactly
 * with the text and are positioned identically on every line.
 */
export default function LineWrapper(props: Props): ReactNode {
  const indentWidth = useIndentGuides();
  if (indentWidth === undefined) {
    return <OriginalLine {...props} />;
  }

  const {line, getTokenProps} = props;
  const first = line[0];
  const leading = first ? first.content.length - first.content.trimStart().length : 0;
  if (!first || leading === 0 || (first.content.trim() === '' && line.length === 1)) {
    return <OriginalLine {...props} />;
  }

  const guideTokens = new Set<Token>();
  const indentTokens: Token[] = [];
  const levels = Math.floor(leading / indentWidth);
  for (let i = 0; i < levels; i++) {
    const token = {...first, content: ' '.repeat(indentWidth), types: [INDENT_TYPE]};
    guideTokens.add(token);
    indentTokens.push(token);
  }
  // Leftover spaces when the indent is not a multiple of the width: no guide
  const remainder = leading - levels * indentWidth;
  const rest = ' '.repeat(remainder) + first.content.slice(leading);
  const newLine = [...indentTokens, ...(rest === '' ? [] : [{...first, content: rest}]), ...line.slice(1)];

  return (
    <OriginalLine
      {...props}
      line={newLine}
      getTokenProps={(input) => {
        const tokenProps = getTokenProps(input);
        if (guideTokens.has(input.token)) {
          return {...tokenProps, className: 'yaml-indent-guide'};
        }
        return tokenProps;
      }}
    />
  );
}
