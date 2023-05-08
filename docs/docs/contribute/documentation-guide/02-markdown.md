# Markdown
Docusaurus uses [standard Markdown syntax](https://daringfireball.net/projects/markdown/syntax) plus [Docusaurus Extended Markdown](https://docusaurus.io/docs/next/markdown-features) functionality.

## Standard Markdown
Here is a quick summary or standard Markdown syntax:

summary = md`
# Markdown summary

| Desired style     | Use the following Markdown annotation                | Produces the following sample HTML                                                                 | 
|-------------------|------------------------------------------------------|----------------------------------------------------------------------------------------------------|
| Heading 1         | `# Title`                                            | `<h1>Title</h1>`                                                                                   |
| Heading 2         | `## Title`                                           | `<h2>Title</h2>`                                                                                   |
| Heading 3         | `### Title`                                          | `<h3>Title</h3>`                                                                                   |
| Heading 4         | `#### Title`                                         | `<h4>Title</h4>`                                                                                   |
| Heading 5         | `##### Title`                                        | `<h5>Title</h5>`                                                                                   |
| Heading 6         | `###### Title`                                       | `<h6>Title</h6>`                                                                                   |
| Paragraph         | `Just start typing`                                  | `<p>Just start typing<p>`                                                                          |
| **Bold**          | `**Text**`                                           | `<strong>Text</strong>`                                                                            |
| *Italic*          | `*Text*`                                             | `<em>Text</em>`                                                                                    |
| ~~Strike~~        | `~~Text~~`                                           | `<del>Text</del>`                                                                                  |
| Quoted (indent)   | `> Text`                                             | `<blockquote><p>Text</p></blockquote>`                                                             |
| ``Code`` (inline) | ``Statement``                                        | `<code>Statement</code>`                                                                           |
| ``Code`` (fenced) | Statement 1<br/>Statement 2<br/>Statement 3          | `<pre><code><span>Statement 1</span><span>Statement 2</span><span>Statement 3</span></code></pre>` |
| List (unordered)  | * List item 1<br/>* List item 2<br/>* List item 3    | `<ul><li>List item 1</li><li>List item 2</li><li>List item 3</li></ul>`                            |
| List (ordered)    | 1. List item 1<br/>2. List item 2<br/>3. List item 3 | `<ul><li>List item 1</li><li>List item 2</li><li>List item 3</li></ul>`                            |
| Images            | `![Alternate text for image](path/to/image)`         | `<img src="path/image.jpg" alt="Alternative text for image>`                                       |
| Hyperlinks        | `[Link text](https://www.google.com/)`               | `<a href="https://www.google.com/">Link text</a>`                                                  |

:::note
You may want to escape special html characters using `\`, and replace the great than symbol with `&lt`, otherwise Docusaurus
will confuse it with html code.
:::

