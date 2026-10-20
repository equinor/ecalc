import type {PrismTheme} from 'prism-react-renderer';

/**
 * Dark code block theme matching the site's dark mode (Infima dark palette).
 *
 * - Background and text use the Infima dark surface/content colours, so code blocks look
 *   like the cards and navbar of the rest of the site.
 * - Token colours mirror the light theme (prism `github`): keys blue, numbers/booleans teal,
 *   strings pink, lightened for the dark background. The teal is the site's dark primary
 *   colour (`--ifm-color-primary-lightest`).
 * - Covers the token types used by YAML (`atrule`, `number`, `boolean`), which the
 *   previous `dracula` theme left uncoloured.
 *
 * All colours have at least 4.5:1 contrast against the background (WCAG AA).
 */
const prismDark: PrismTheme = {
  plain: {
    color: '#e3e3e3', // --ifm-color-content (dark)
    backgroundColor: '#242526', // --ifm-background-surface-color (dark)
  },
  styles: [
    {
      types: ['comment', 'prolog', 'doctype', 'cdata'],
      style: {color: '#8d949e', fontStyle: 'italic'}, // --ifm-color-gray-600
    },
    {
      types: ['namespace'],
      style: {opacity: 0.7},
    },
    {
      types: ['string', 'attr-value'],
      style: {color: '#f47fae'},
    },
    {
      types: ['punctuation', 'operator'],
      style: {color: '#bec3c9'}, // --ifm-color-gray-500
    },
    {
      types: ['entity', 'url', 'symbol', 'number', 'boolean', 'variable', 'constant', 'property', 'regex', 'inserted'],
      style: {color: '#4fddbf'}, // --ifm-color-primary-lightest (dark)
    },
    {
      types: ['atrule', 'keyword', 'attr-name', 'selector'],
      style: {color: '#4fb3e8'},
    },
    {
      types: ['function', 'deleted', 'tag'],
      style: {color: '#ff7b72'},
    },
    {
      types: ['function-variable'],
      style: {color: '#b392f0'},
    },
  ],
};

export default prismDark;
