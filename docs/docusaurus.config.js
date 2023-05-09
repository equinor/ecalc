// @ts-check
// Note: type annotations allow type checking and IDEs autocompletion

const lightCodeTheme = require('prism-react-renderer/themes/github');
const darkCodeTheme = require('prism-react-renderer/themes/dracula');
const math = require('remark-math');
const katex = require('rehype-katex');

async function createConfig() {
  const mdxMermaid = await import('mdx-mermaid');
  return {
    title: 'eCalc™ Docs',
    tagline: 'Documentation for eCalc™',
    url: 'https://equinor.github.io',
    baseUrl: '/ecalc',
    onBrokenLinks: 'throw',
    onBrokenMarkdownLinks: 'warn',
    favicon: 'img/favicon.svg',

    // GitHub pages deployment config.
    // If you aren't using GitHub pages, you don't need these.
    organizationName: 'equinor', // Usually your GitHub org/user name.
    projectName: 'ecalc', // Usually your repo name.
    deploymentBranch: 'gh-pages',

    // Even if you don't use internalization, you can use this field to set useful
    // metadata like html lang. For example, if your site is Chinese, you may want
    // to replace "en" with "zh-Hans".
    i18n: {
      defaultLocale: 'en',
      locales: ['en'],
    },

    presets: [
      [
        'classic',
        /** @type {import('@docusaurus/preset-classic').Options} */
        ({
          docs: {
            sidebarPath: require.resolve('./sidebars.js'),
            editUrl:
              'https://github.com/equinor/ecalc/tree/main/documentation/',
            remarkPlugins: [mdxMermaid.default, math],
            rehypePlugins: [katex],
          },
          blog: false,
          theme: {
            customCss: require.resolve('./src/css/custom.css'),
          },
        }),
      ],
    ],

    themeConfig:
      /** @type {import('@docusaurus/preset-classic').ThemeConfig} */
      ({
        navbar: {
          title: '',
          logo: {
            alt: 'eCalc Logo',
            src: 'img/logo.svg',
            href: '/',
          },
          items: [
            {
              type: 'docSidebar',
              sidebarId: 'about',
              position: 'left',
              label: 'Docs',
            },
            {
              type: 'docSidebar',
              sidebarId: 'contribute',
              position: 'left',
              label: 'Contribute',
            },
            {
              type: 'docSidebar',
              sidebarId: 'changelog',
              position: 'left',
              label: 'Changelog',
            },
            {
              href: 'https://github.com/equinor/ecalc',
              label: 'GitHub',
              position: 'right',
            },
          ],
        },
        footer: {
          style: 'dark',
          links: [
            {
              title: 'More',
              items: [
                {
                  label: 'GitHub',
                  href: 'https://github.com/equinor/ecalc',
                },
              ],
            },
          ],
          copyright: `eCalc™ Copyright © ${new Date().getFullYear()} Equinor ASA. Built with Docusaurus.`,
        },
        prism: {
          theme: lightCodeTheme,
          darkTheme: darkCodeTheme,
          magicComments: [
            // Remember to extend the default highlight class name as well!
            {
              className: 'theme-code-block-highlighted-line',
              line: 'highlight-next-line',
              block: { start: 'highlight-start', end: 'highlight-end' },
            },
            {
              className: 'code-block-old-line',
              line: 'This is old',
              block: { start: 'highlight-old-start', end: 'highlight-old-end' },
            },
            {
              className: 'code-block-new-line',
              line: 'This is new',
              block: { start: 'highlight-new-start', end: 'highlight-new-end' },
            },
          ],
        },
      }),
    stylesheets: [
      {
        href: '/katex/katex.min.css',
        type: 'text/css',
      },
    ],
    themes: [
      // ... Your other themes.
      [
        require.resolve('@easyops-cn/docusaurus-search-local'),
        /** @type {import("@easyops-cn/docusaurus-search-local").PluginOptions} */
        ({
          // `hashed` is recommended as long-term-cache of index file is possible.
          hashed: true,
          explicitSearchResultPath: true,
        }),
      ],
    ],
  };
}

module.exports = createConfig;
