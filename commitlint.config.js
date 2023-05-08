module.exports = {
  extends: ['@commitlint/config-conventional'], // https://github.com/conventional-changelog/commitlint/blob/master/%40commitlint/config-conventional/index.js
  rules: {
    'scope-enum': [
      2,
      'always',
      [
        'libecalc',
        'libecalc.core',
        'libecalc.fixtures',
        'libecalc.common',
        'libecalc.services',
        'libecalc.dto',
        'libecalc.expression',
        'libecalc.input',
        'libecalc.output',
        'cli',
        'docs',
      ],
    ],
  },
};
