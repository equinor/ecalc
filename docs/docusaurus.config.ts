import type {Config} from '@docusaurus/types';
import type * as Preset from '@docusaurus/preset-classic';

import {themes as prismThemes} from 'prism-react-renderer';
import math from 'remark-math';
import katex from 'rehype-katex';
import localSearch from '@easyops-cn/docusaurus-search-local';

const baseUrl = "/ecalc"

const config: Config = {
  title: 'eCalc™ Docs',
  tagline: 'Documentation for eCalc™',
  url: 'https://equinor.github.io',
  baseUrl: baseUrl,
  onBrokenLinks: 'throw',
  onBrokenAnchors: 'throw',
  onBrokenMarkdownLinks: 'throw',
  onDuplicateRoutes: 'throw',
  favicon: 'img/favicon.svg',

  // GitHub pages deployment config.
  organizationName: 'equinor',
  projectName: 'ecalc',
  deploymentBranch: 'gh-pages',

  markdown: {
    mermaid: true,
  },

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
      ({
        docs: {
          sidebarPath: './sidebars.ts',
          editUrl:
            'https://github.com/equinor/ecalc/tree/main/documentation/',
          remarkPlugins: [math],
          rehypePlugins: [katex],
        },
        blog: false,
        theme: {
          customCss: require.resolve('./src/css/custom.css'),
        },
      }),
    ],
  ],
  themeConfig: {
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
        theme: prismThemes.github,
        darkTheme: prismThemes.dracula,
        magicComments: [
          // Remember to extend the default highlight class name as well!
          {
            className: 'theme-code-block-highlighted-line',
            line: 'highlight-next-line',
            block: {start: 'highlight-start', end: 'highlight-end'},
          },
          {
            className: 'code-block-old-line',
            line: 'This is old',
            block: {start: 'highlight-old-start', end: 'highlight-old-end'},
          },
          {
            className: 'code-block-new-line',
            line: 'This is new',
            block: {start: 'highlight-new-start', end: 'highlight-new-end'},
          },
        ],
      },
    } satisfies Preset.ThemeConfig,
  stylesheets: [
    {
      href: 'https://cdn.jsdelivr.net/npm/katex@0.16.10/dist/katex.min.js',
      type: 'text/css',
      integrity:
        'sha384-hIoBPJpTUs74ddyc4bFZSM1TVlQDA60VBbJS0oA934VSz82sBx1X7kSx2ATBDIyd',
      crossorigin: 'anonymous',
    },
  ],
  themes: [
    // ... Your other themes.
    '@docusaurus/theme-mermaid',
    [
      localSearch,
      ({
        // `hashed` is recommended as long-term-cache of index file is possible.
        hashed: true,
        explicitSearchResultPath: true,
      }),
    ],
  ],
};

export default config;
