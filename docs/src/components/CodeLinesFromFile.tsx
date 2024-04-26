import CodeBlock, {Props} from '@theme/CodeBlock';

interface CodeLinesFromFileProps extends Props {
  start: number;
  end: number;
  children: string;
}

function CodeLinesFromFile({start, end, children, ...props}: CodeLinesFromFileProps) {
  const linesToRender = children.split("\n").slice(start - 1, end).join("\n");
  return <CodeBlock {...props}>{linesToRender}</CodeBlock>;
}

export default CodeLinesFromFile;
