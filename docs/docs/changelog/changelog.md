# Changelog

## [8.2.2](https://github.com/equinor/ecalc/compare/v8.2.1...v8.2.2) (2023-05-28)


### Bug Fixes

* allow electrical driven consumers in consumer system v2 ([92cb4fa](https://github.com/equinor/ecalc/commit/92cb4faa7bfa525af6527892eab2dd38606b2033))
* cast float to numpy array in function call ([#39](https://github.com/equinor/ecalc/issues/39)) ([250928c](https://github.com/equinor/ecalc/commit/250928c2b573f6148129ec32bc54932cbb2cb4a0))
* **NeqSim Wrapper:** inconsistent return type ([9482421](https://github.com/equinor/ecalc/commit/94824210b4c2da666d9280ee581e3a98463e4742))
* output emissions in fixed and predicted order ([059dab5](https://github.com/equinor/ecalc/commit/059dab592bf396eb20d4b825b8358fc10793ca5d))


### Continuous Integration

* enable mypy for neqsim wrapper ([871c038](https://github.com/equinor/ecalc/commit/871c038c756ba40fc1c43bfbee7f83b0f4fd5390))
* parallelize tests in docker ([4e73b68](https://github.com/equinor/ecalc/commit/4e73b680147c558e4e7cb0d44a78cfaa0e1a357f))
* remove docker tests ([a2b5c1a](https://github.com/equinor/ecalc/commit/a2b5c1a7158d81094982724a63748ca4798f14ca))
* use xdist to parallelize test suite ([2895ae7](https://github.com/equinor/ecalc/commit/2895ae7361878ea94d0d5be4a04a6ffbe0067b3d))


### Tests

* compare consumer system v1 vs v2 both fuel and power consumers ([74fafce](https://github.com/equinor/ecalc/commit/74fafce276b93c9495bcfa1c2800c2a866bfa388))


### Code Refactoring

* even more typing! ([a7b22e2](https://github.com/equinor/ecalc/commit/a7b22e23fa73d4e0cd35750f7ea6cea5e52f8abd))
* fix more typing ([08394a3](https://github.com/equinor/ecalc/commit/08394a3ce3969976674532ccf8c3876265315035))
* make units lowercase in function names ([272f0d7](https://github.com/equinor/ecalc/commit/272f0d7274986bc54c0717e7964d5a48c9a06723))
* raise exceptions from error ([ee6e474](https://github.com/equinor/ecalc/commit/ee6e4742da1c3201abe8969d2dfedb1c2d4b369b))
* remove duplicate function for converting to standard rate ([93de4f4](https://github.com/equinor/ecalc/commit/93de4f4d10b10763428d933e7afc3dea277a31ac))
* remove unused code ([7ccf2c1](https://github.com/equinor/ecalc/commit/7ccf2c1dfd6d51242032d1b7bf45c52f6b7e90f5))
* rename function variables ([c56693a](https://github.com/equinor/ecalc/commit/c56693a9e982c7e2275cc277939624c7812e9b65))
* typing and typos ([936b941](https://github.com/equinor/ecalc/commit/936b9417da0723871d6c46f258d256a8967f934c))


### Documentation

* add docstrings to undocumented functions ([064adfa](https://github.com/equinor/ecalc/commit/064adfa204c2c9f21588c30dc2c2cf3d2375c8a7))
* update compressor pressure control ([#14](https://github.com/equinor/ecalc/issues/14)) ([1da1999](https://github.com/equinor/ecalc/commit/1da1999ac4dfaf21abd50e9d9ecc94102a0427e2))


### Miscellaneous Chores

* add consumer function utils ([50e2d66](https://github.com/equinor/ecalc/commit/50e2d667a37fc5f09a4c76615be0b21a42e2c703))
* add consumer system v2 sub results ([b78b035](https://github.com/equinor/ecalc/commit/b78b03504c4a46114062aded6661f00400c6ca06))
* add testing of condition in consumer system consumer function ([50e2d66](https://github.com/equinor/ecalc/commit/50e2d667a37fc5f09a4c76615be0b21a42e2c703))
* capture return values from a decorated function ([09ef23e](https://github.com/equinor/ecalc/commit/09ef23e92bf2755c7b83c7de5e9cbe9ee862db05)), closes [#4489](https://github.com/equinor/ecalc/issues/4489)
* capture valid neqsim states ([f9c8b09](https://github.com/equinor/ecalc/commit/f9c8b09f36d1f9a965b94cd32ef2d7b47c910a75))
* change to absolute image links in readme ([#16](https://github.com/equinor/ecalc/issues/16)) ([9a54f51](https://github.com/equinor/ecalc/commit/9a54f516613509bd6d5595f8afc1e5dce7ac860a))
* conditions in tabular consumer function ([50e2d66](https://github.com/equinor/ecalc/commit/50e2d667a37fc5f09a4c76615be0b21a42e2c703))
* correct link to documentation from README.md ([f185a7f](https://github.com/equinor/ecalc/commit/f185a7f8c389d4f9f5e087b68bfc83cc4fddad74))
* coverage from coverage.py is not directly supported ([8e76c8a](https://github.com/equinor/ecalc/commit/8e76c8ab90d455613868e4343d6a2f61ccfb2a68))
* enable B904 ([65ac18b](https://github.com/equinor/ecalc/commit/65ac18ba23178c57886c1a77b74b2ee52c6d7a60))
* evaluate consumer system v2 consumers according to input order ([0088232](https://github.com/equinor/ecalc/commit/00882321d823f74cf37f0b42e9771775b8eb34db))
* fix badges ([dd2fd6b](https://github.com/equinor/ecalc/commit/dd2fd6be194d306ae1ef969b13c43aea7352db58))
* migration guide changed resampling method ([#38](https://github.com/equinor/ecalc/issues/38)) ([d4f11dc](https://github.com/equinor/ecalc/commit/d4f11dc49ce5eef29f6982f9514f6664ef18c764))
* move conditioning for consumer system consumer function ([50e2d66](https://github.com/equinor/ecalc/commit/50e2d667a37fc5f09a4c76615be0b21a42e2c703))
* move conditions for compressor consumer function ([50e2d66](https://github.com/equinor/ecalc/commit/50e2d667a37fc5f09a4c76615be0b21a42e2c703))
* move conditions for direct consumer function ([50e2d66](https://github.com/equinor/ecalc/commit/50e2d667a37fc5f09a4c76615be0b21a42e2c703))
* move conditions in pump consumer function ([50e2d66](https://github.com/equinor/ecalc/commit/50e2d667a37fc5f09a4c76615be0b21a42e2c703))
* move evaluation of conditions before calculations ([#24](https://github.com/equinor/ecalc/issues/24)) ([50e2d66](https://github.com/equinor/ecalc/commit/50e2d667a37fc5f09a4c76615be0b21a42e2c703))
* remove energy usage before conditioning from tests ([50e2d66](https://github.com/equinor/ecalc/commit/50e2d667a37fc5f09a4c76615be0b21a42e2c703))
* remove energy_usage_before_conditioning from results ([50e2d66](https://github.com/equinor/ecalc/commit/50e2d667a37fc5f09a4c76615be0b21a42e2c703))
* set power to zero when rate (and fuel consumption) is zero ([#27](https://github.com/equinor/ecalc/issues/27)) ([1ee5bfd](https://github.com/equinor/ecalc/commit/1ee5bfd2af30482683698172cd2a9c512f793b77))
* typo ([9c3af00](https://github.com/equinor/ecalc/commit/9c3af00b4bcf5e3e57a99c97d3cc9028faeca307))
* typo ([389db6f](https://github.com/equinor/ecalc/commit/389db6f29e7a7ff9044b7bac5fb0e6fddba1687d))
* update dependencies to latest compatible ([5809862](https://github.com/equinor/ecalc/commit/58098624c64693d20591bc96d79c2cbc61e3b5a6))
* update description etc in readme ([f37dbb7](https://github.com/equinor/ecalc/commit/f37dbb7b97ade6c358b89e288ba644b06d546187))
* update docstring for numeric_methods ([be435c3](https://github.com/equinor/ecalc/commit/be435c3c96bc378614c4f761410c005be77025a4))
* update test snapshots ([1ee5bfd](https://github.com/equinor/ecalc/commit/1ee5bfd2af30482683698172cd2a9c512f793b77))

## 8.2.1 (2023-05-09)


### Miscellaneous Chores

* initial commit ([e4a59f0](https://github.com/equinor/ecalc/commit/e4a59f03f716c7ceb1d3df50af6ef3cc76c405cd))
* release 8.2.1 ([9d66de6](https://github.com/equinor/ecalc/commit/9d66de6199b35d3bfd279fd1fe96806b05e6d594))
* update documentation url ([6443ecf](https://github.com/equinor/ecalc/commit/6443ecf7324e6ee33d02bfa1a3f7b9168f19a612))


### Continuous Integration

* enable publish to pypi ([#15](https://github.com/equinor/ecalc/issues/15)) ([fe6f069](https://github.com/equinor/ecalc/commit/fe6f069b12119b62d054a635eb038b37a4394415))
