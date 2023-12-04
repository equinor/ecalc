# Changelog

## [8.7.0](https://github.com/equinor/ecalc/compare/v8.6.0...v8.7.0)


### ⚠ BREAKING CHANGES

* Change name from DIRECT_EMITTERS to VENTING_EMITTERS in input Yaml-file ([#303](https://github.com/equinor/ecalc/pull/303))

## [8.6.0](https://github.com/equinor/ecalc/compare/v8.5.0...v8.6.0) (2023-11-21)


### ⚠ BREAKING CHANGES

* remove economy from ecalc ([#282](https://github.com/equinor/ecalc/issues/282))
* graph.components and graph.get_component renamed to nodes and get_node
* add type to consumers in system

### Features

* expose yaml variables ([1fe9dd0](https://github.com/equinor/ecalc/commit/1fe9dd0e3ceae658afaba24a2b18b91b3a11da43))
* include rate type in header for csv export ([#279](https://github.com/equinor/ecalc/issues/279)) ([5edd0cc](https://github.com/equinor/ecalc/commit/5edd0ccff2b2f1dbfe746a666266b59c714a5eef))
* support bfs_tree in graph ([a4fff16](https://github.com/equinor/ecalc/commit/a4fff168dfa32d04588bb7e3b71de8c12e9dd6d0))
* train v2 yaml and dto ([#272](https://github.com/equinor/ecalc/issues/272)) ([b0e3466](https://github.com/equinor/ecalc/commit/b0e346618bb3b39a186eb814dd40be2f7d905122))


### Bug Fixes

* ensure that start date in global time vector is consistent with the requested output frequency ([#269](https://github.com/equinor/ecalc/issues/269)) ([e8ef9b9](https://github.com/equinor/ecalc/commit/e8ef9b98901603c0a9e328c2c8923c5facca962c))
* make iteration loops for simplified train consistent ([#263](https://github.com/equinor/ecalc/issues/263)) ([b066c74](https://github.com/equinor/ecalc/commit/b066c74e41fcbb6c32e51781c0225490f61e9690))
* wrong handling of values and timesteps in temporal models ([#261](https://github.com/equinor/ecalc/issues/261)) ([4e20264](https://github.com/equinor/ecalc/commit/4e202648e6288508d67fee52c651d125166e68e7))


### Documentation

* update changelog ([#264](https://github.com/equinor/ecalc/issues/264)) ([22ef8f7](https://github.com/equinor/ecalc/commit/22ef8f7ca2a1e1800050c8f55624677a2f282e43))


### Miscellaneous Chores

* add INVALID_INPUT and INVALID_MAX_RATE ([d651ed6](https://github.com/equinor/ecalc/commit/d651ed6822ba180ba4a490e1245a0f406cc64e43))
* add test of get_max_standard_rate for single speed compressor train ([d651ed6](https://github.com/equinor/ecalc/commit/d651ed6822ba180ba4a490e1245a0f406cc64e43))
* clean up common module ([#277](https://github.com/equinor/ecalc/issues/277)) ([e1959ab](https://github.com/equinor/ecalc/commit/e1959aba2a91c4abec2d820b6cb9378ac1dea281))
* extend tests of time series resampling ([e8ef9b9](https://github.com/equinor/ecalc/commit/e8ef9b98901603c0a9e328c2c8923c5facca962c))
* improve algorithm to generate generic variable speed compressor charts from input points ([#276](https://github.com/equinor/ecalc/issues/276)) ([b257567](https://github.com/equinor/ecalc/commit/b257567230000a92b5fcca8f8becdbcc4c880092))
* make sure no mismatch between timestamps and time series values ([#251](https://github.com/equinor/ecalc/issues/251)) ([ae6ade9](https://github.com/equinor/ecalc/commit/ae6ade9fafb9b0ccf2afec5e633c2190a2f1009b))
* only calculate max standard rate for time steps with valid model input ([#252](https://github.com/equinor/ecalc/issues/252)) ([d651ed6](https://github.com/equinor/ecalc/commit/d651ed6822ba180ba4a490e1245a0f406cc64e43))
* possibility to include start and end date in resampling ([e8ef9b9](https://github.com/equinor/ecalc/commit/e8ef9b98901603c0a9e328c2c8923c5facca962c))
* update changelog for v8.6 release ([#288](https://github.com/equinor/ecalc/issues/288)) ([af32274](https://github.com/equinor/ecalc/commit/af32274c17cb8a84895bf85c7b83360cd76bc533))
* update dependencies for new v8.6 release ([#289](https://github.com/equinor/ecalc/issues/289)) ([5a245a3](https://github.com/equinor/ecalc/commit/5a245a397761ed69c2ffab151a7a33567f3c7282))


### Code Refactoring

* add option to skip header validation on resource files ([#260](https://github.com/equinor/ecalc/issues/260)) ([883b7e6](https://github.com/equinor/ecalc/commit/883b7e6888d5ff4ddca41cbeac0f7c7dd96e60a6))
* calculate timesteps separately ([#284](https://github.com/equinor/ecalc/issues/284)) ([bd9d684](https://github.com/equinor/ecalc/commit/bd9d684467698edbd88d7a089846310b3cea5ea4))
* collect results in priority optimizer ([16b9ccc](https://github.com/equinor/ecalc/commit/16b9ccc3687a6f2910c1df5602c82dd75706089b))
* common consumer system type ([fe09263](https://github.com/equinor/ecalc/commit/fe09263acaf8d3ea8518759e695d6f368dfb214a))
* common yaml system v2 class ([98198fc](https://github.com/equinor/ecalc/commit/98198fc7a19575f6b949527993999ae929a7590c))
* consistent naming of nodes in graph ([676c7b8](https://github.com/equinor/ecalc/commit/676c7b84f99e1ca79446321ab06eba43df36abef))
* generic graph class ([6f63e40](https://github.com/equinor/ecalc/commit/6f63e40af1b2f57380852ef6403b6f4ac2474d50))
* move into presentation layer ([#271](https://github.com/equinor/ecalc/issues/271)) ([52530e0](https://github.com/equinor/ecalc/commit/52530e0b72aa0f07de93b6c231798dd5c9a20eb4))
* remove economy from ecalc ([#282](https://github.com/equinor/ecalc/issues/282)) ([a50148c](https://github.com/equinor/ecalc/commit/a50148c8bce3bfdb491dbab65620ac964a80e65c))
* rename Stream to StreamConditions ([cf908ec](https://github.com/equinor/ecalc/commit/cf908ece731c6dcd2755ed6b08b8748cff5ac508))
* rename to component graph ([9629f22](https://github.com/equinor/ecalc/commit/9629f221a0370559a7b89bbede0b5576eb916c20))
* system v2 stream conditions format ([#257](https://github.com/equinor/ecalc/issues/257)) ([e228e8b](https://github.com/equinor/ecalc/commit/e228e8b1180a3dd22a408fa199e52797aef43fc6))
* use common consumer system dto class ([#267](https://github.com/equinor/ecalc/issues/267)) ([3c58b53](https://github.com/equinor/ecalc/commit/3c58b53e0731cbae9219bfb6eef96e5e5d4ea144))
* use PriorityOptimizer outside ConsumerSystem ([f1af9e6](https://github.com/equinor/ecalc/commit/f1af9e6c701d8899450aacaa94ba02071b032dc6))

## [8.5.0](https://github.com/equinor/ecalc/compare/v8.4.0...v8.5.0) (2023-10-30)


### Features

* add pump results to system v2 ([8cf9e1b](https://github.com/equinor/ecalc/commit/8cf9e1b0d3ab8438291303663fc83092de1c808a))
* add stream conditions to compressor v2 ([#194](https://github.com/equinor/ecalc/issues/194)) ([232f83b](https://github.com/equinor/ecalc/commit/232f83bf91044b706ba4c7715ceddf71f9456644))
* multiple streams in system ([#242](https://github.com/equinor/ecalc/issues/242)) ([419c2e9](https://github.com/equinor/ecalc/commit/419c2e9cef6f6bb768b5e140a5092650cacd245b))
* support name for crossover streams ([#236](https://github.com/equinor/ecalc/issues/236)) ([c801f3f](https://github.com/equinor/ecalc/commit/c801f3f0fa4b967c15c5122ac8997695f38bae12))


### Bug Fixes

* don't require HCEXPORT in editor ([#254](https://github.com/equinor/ecalc/issues/254)) ([e497245](https://github.com/equinor/ecalc/commit/e497245c9ec4e6d10e9def5999d24c5e0ba58134))
* ensure unique names in system v2 ([#238](https://github.com/equinor/ecalc/issues/238)) ([3634a9e](https://github.com/equinor/ecalc/commit/3634a9e1a4f2a4181ea1679fa1edcce0bb57a06e))
* rate when multiple streams model ([#214](https://github.com/equinor/ecalc/issues/214)) ([892720e](https://github.com/equinor/ecalc/commit/892720e781978be0210b7488ad6c68466db51700))
* set_regularity fixture ([#213](https://github.com/equinor/ecalc/issues/213)) ([e9ea04f](https://github.com/equinor/ecalc/commit/e9ea04f74c2262343fbde5d5aed46ffc15404e29))
* update ecalc validation for yaml file in web ([#243](https://github.com/equinor/ecalc/issues/243)) ([2981f2c](https://github.com/equinor/ecalc/commit/2981f2c71b7aba0271f72c8ec5f1d764a0d36387))
* use file reference instead of urls in docs ([#216](https://github.com/equinor/ecalc/issues/216)) ([35c4f68](https://github.com/equinor/ecalc/commit/35c4f6853c9452d1963daf321cce3e2ebe087f9e))
* wrong data for boilers and heaters in ltp-results ([#237](https://github.com/equinor/ecalc/issues/237)) ([851e831](https://github.com/equinor/ecalc/commit/851e83141c1971a8fc1fdec47e05b4e5a26d0861))


### Documentation

* add missing keywords surge control margin ([#239](https://github.com/equinor/ecalc/issues/239)) ([8b97673](https://github.com/equinor/ecalc/commit/8b97673b001231b6960bda817d50241135df65df))
* update changelog for upcoming release v8.4 ([#203](https://github.com/equinor/ecalc/issues/203)) ([66671e0](https://github.com/equinor/ecalc/commit/66671e07ce678f4444f6428b776b60c607d35957))


### Miscellaneous Chores

* add __init__ file to ecalc_cli ([af6bee9](https://github.com/equinor/ecalc/commit/af6bee96ae3ac69137f38117013a305f474acd87))
* add chart area flag to test of full recirculation ([0c45251](https://github.com/equinor/ecalc/commit/0c452515226beec76a4db3c674d4fa102771dbe7))
* add check for zero efficiency in stage ([3ea3035](https://github.com/equinor/ecalc/commit/3ea3035c659ee922a41c70b157f9d6a1a1f8214d))
* add dependabot actions monitoring ([#219](https://github.com/equinor/ecalc/issues/219)) ([d5f5dfd](https://github.com/equinor/ecalc/commit/d5f5dfd12103fb60104057fd2f3b5ce4484e3494))
* add ModelInputFailureStatus ([6b0c728](https://github.com/equinor/ecalc/commit/6b0c72875e667ca1abce5b9b1f2ef4a9548d0d1e))
* add NO_FLOW ChartAreaFlag ([0c45251](https://github.com/equinor/ecalc/commit/0c452515226beec76a4db3c674d4fa102771dbe7))
* add rate type to pump model result ([#209](https://github.com/equinor/ecalc/issues/209)) ([21deeb7](https://github.com/equinor/ecalc/commit/21deeb7a70cd64f47db87494314a0119ee4598d5))
* **cli:** add all energy usage models load_results test ([#220](https://github.com/equinor/ecalc/issues/220)) ([e09febb](https://github.com/equinor/ecalc/commit/e09febb517a62d27e2d794946d016f1ba0af8fd1))
* **deps:** bump actions/cache from 3.0.11 to 3.3.2 ([#223](https://github.com/equinor/ecalc/issues/223)) ([087867c](https://github.com/equinor/ecalc/commit/087867c19fc087702ae7829b3d6cddfc1ac62f9d))
* **deps:** bump actions/checkout from 2 to 4 ([#221](https://github.com/equinor/ecalc/issues/221)) ([bcc2f81](https://github.com/equinor/ecalc/commit/bcc2f81d9eed20f3021c1e13fead3f8c8d009267))
* **deps:** bump actions/setup-node from 3 to 4 ([cb7e816](https://github.com/equinor/ecalc/commit/cb7e816932e73d091cfa4211abe086620ab320fd))
* **deps:** bump snok/install-poetry from 1.3.3 to 1.3.4 ([#222](https://github.com/equinor/ecalc/issues/222)) ([80dab72](https://github.com/equinor/ecalc/commit/80dab720f352995121a1cd470e14eef9779a45fb))
* fix tests ([6b0c728](https://github.com/equinor/ecalc/commit/6b0c72875e667ca1abce5b9b1f2ef4a9548d0d1e))
* handle requested pressures correct for compressors without system ([#233](https://github.com/equinor/ecalc/issues/233)) ([445fc9d](https://github.com/equinor/ecalc/commit/445fc9d856db729181e48f04d58cf05d324a8c50))
* handle requested pressures for compressor systems ([#215](https://github.com/equinor/ecalc/issues/215)) ([6b05439](https://github.com/equinor/ecalc/commit/6b054390fe86fe5067a908854f0dd6d48ba114ff))
* more robust surge control margin calculation ([#229](https://github.com/equinor/ecalc/issues/229)) ([74b4e59](https://github.com/equinor/ecalc/commit/74b4e599ff2336567e7a86e57bb4287030ccea08))
* move feature experimental to main method for requested pressures ([#230](https://github.com/equinor/ecalc/issues/230)) ([00ad854](https://github.com/equinor/ecalc/commit/00ad854cc23822690e662338f6592142344a59f3))
* pre-commit ([a310df2](https://github.com/equinor/ecalc/commit/a310df21ebb9dc27e9999b577cc7ae7a106aa68c))
* show correct version ([#211](https://github.com/equinor/ecalc/issues/211)) ([f8de992](https://github.com/equinor/ecalc/commit/f8de992b6d2621a604f9b31b6eea0ff644df30dd))
* update dependencies ([#212](https://github.com/equinor/ecalc/issues/212)) ([c9b8506](https://github.com/equinor/ecalc/commit/c9b850672357fd48a0b1f40f5b429ae615fbd914))
* update dependencies ([#259](https://github.com/equinor/ecalc/issues/259)) ([e7f031f](https://github.com/equinor/ecalc/commit/e7f031f73dc3320352cd6087e32b281dbf01e6bc))
* update python deps ([#247](https://github.com/equinor/ecalc/issues/247)) ([514da16](https://github.com/equinor/ecalc/commit/514da161158200bc18a8963cb10be141c9847fb8))
* update system v2 tests to only use one crossover ([#205](https://github.com/equinor/ecalc/issues/205)) ([aa65163](https://github.com/equinor/ecalc/commit/aa6516367fd217b3868af2c1b56119ec548c77ad))
* update zero efficiency error message ([#258](https://github.com/equinor/ecalc/issues/258)) ([5be6fe4](https://github.com/equinor/ecalc/commit/5be6fe433791bee1f25dfcc265ffb94c87633836))
* upgrade packages ([#255](https://github.com/equinor/ecalc/issues/255)) ([035aad1](https://github.com/equinor/ecalc/commit/035aad15b41bb16676ec33d33dcb78d139e2bc6c))
* version must be updated in version.py ([63eb672](https://github.com/equinor/ecalc/commit/63eb672ff5a28c5c4b14294c8d9dcc38a3481089))
* warn user about full recirculation of fluids in a compressor stage in a multiple streams and pressures compressor train ([#196](https://github.com/equinor/ecalc/issues/196)) ([0c45251](https://github.com/equinor/ecalc/commit/0c452515226beec76a4db3c674d4fa102771dbe7))


### Code Refactoring

* implement evaluate streams in models ([#232](https://github.com/equinor/ecalc/issues/232)) ([df6b6b0](https://github.com/equinor/ecalc/commit/df6b6b01099fe87738594544512c28d0bceb0d07))
* **libecalc.core:** stream as input ([#224](https://github.com/equinor/ecalc/issues/224)) ([e06f970](https://github.com/equinor/ecalc/commit/e06f970147e5539fa2c8db0ca53675d24c56ae33))
* move crossover to component_conditions for system v2 ([#204](https://github.com/equinor/ecalc/issues/204)) ([018b472](https://github.com/equinor/ecalc/commit/018b47291cbfd5b8b92bbff9c79846b32696d316))
* move RateType into common module ([#253](https://github.com/equinor/ecalc/issues/253)) ([c7f5a99](https://github.com/equinor/ecalc/commit/c7f5a9955c55fdc970f60b6aade8a0793acab27a))
* move validate operational conditions from compressor train, rename to validate model input ([#256](https://github.com/equinor/ecalc/issues/256)) ([6b0c728](https://github.com/equinor/ecalc/commit/6b0c72875e667ca1abce5b9b1f2ef4a9548d0d1e))
* remove regularity our of core/domain ([#246](https://github.com/equinor/ecalc/issues/246)) ([714888b](https://github.com/equinor/ecalc/commit/714888bfa69460174c1b3917470018e8e688b3e1))
* remove temporal operational settings system v2 ([#244](https://github.com/equinor/ecalc/issues/244)) ([a1d2ce6](https://github.com/equinor/ecalc/commit/a1d2ce62c4cfde50665bd1fdfa41402a64548672))
* rename streamCondition to stream ([32885b5](https://github.com/equinor/ecalc/commit/32885b5b054008cbfb682454daaa29d443fd561f))
* separate optimization from system ([#245](https://github.com/equinor/ecalc/issues/245)) ([b580e3d](https://github.com/equinor/ecalc/commit/b580e3d80ab5392410c438f6ff355fdf1326f121))
* use Graph object to build graph ([#250](https://github.com/equinor/ecalc/issues/250)) ([ce65dba](https://github.com/equinor/ecalc/commit/ce65dbad024fc9afae74a2c533767152ce2efa20))

## [8.4.0](https://github.com/equinor/ecalc/compare/v8.3.0...v8.4.0) (2023-09-25)


### Features

* add compressor inlet- and outlet pressures to models/train level ([#152](https://github.com/equinor/ecalc/issues/152)) ([9b95ee5](https://github.com/equinor/ecalc/commit/9b95ee50fd78d77c59dfe2533c10dbcdc41461a7))
* add input compressor pressures to output ([#140](https://github.com/equinor/ecalc/issues/140)) ([74e3e56](https://github.com/equinor/ecalc/commit/74e3e5673bad36bf30d8b217609819a79d7e76bb))
* add support for system v2 in FDE ([e6d1f93](https://github.com/equinor/ecalc/commit/e6d1f938d62d68479835f90932bc09b49203a6c9))
* add support for temporal operational settings in v2 ([f2b217a](https://github.com/equinor/ecalc/commit/f2b217acaaf445df03fba077cd7407a4c37375d2))


### Bug Fixes

* add system v2 subcomponents to components list ([b61a0fe](https://github.com/equinor/ecalc/commit/b61a0feba9d28c27992128a2e02262c58dedcbdb))
* add system v2 to generator set consumers ([#166](https://github.com/equinor/ecalc/issues/166)) ([d40558e](https://github.com/equinor/ecalc/commit/d40558eb0c727723ba1cf952dfbd58b73dca0cd0))
* avoid name conflicts with ecalc cli package ([#197](https://github.com/equinor/ecalc/issues/197)) ([140c448](https://github.com/equinor/ecalc/commit/140c4481b8a860b203b338b51a883c41bd6b4dc6))
* bug in asset_result_dto ([#170](https://github.com/equinor/ecalc/issues/170)) ([c45a7ac](https://github.com/equinor/ecalc/commit/c45a7acfb4bf3c89f8c89e71561a90e2831ccb17))
* correct type for total system rate in pump system v2 ([#167](https://github.com/equinor/ecalc/issues/167)) ([5559cdd](https://github.com/equinor/ecalc/commit/5559cdd478511b050a3f344da33110621f221b76))
* do not return actual rate in results for compressor sampled since it can not be calculated ([#190](https://github.com/equinor/ecalc/issues/190)) ([74fcfd8](https://github.com/equinor/ecalc/commit/74fcfd8ffc4835d6ddec442374f1389f24df66d7))
* expression type in system v2 ([5318fb5](https://github.com/equinor/ecalc/commit/5318fb536945cd2aeb82f03cb922fa1a4ed950e1))
* forbid extra attributes in TimeSeries ([#195](https://github.com/equinor/ecalc/issues/195)) ([24c27bb](https://github.com/equinor/ecalc/commit/24c27bb0d3f9ee5570dc76e6d6cf3a45bc006e27))
* full run with system v2 components ([#147](https://github.com/equinor/ecalc/issues/147)) ([2279ef4](https://github.com/equinor/ecalc/commit/2279ef430f04673bc91926316663cdbd97cfc61d))
* generate system v2 schema ([#161](https://github.com/equinor/ecalc/issues/161)) ([a27c392](https://github.com/equinor/ecalc/commit/a27c39253d91a3f1c7cc559164874c2d5f9443d3))
* handle all situations where zero mass rate is entering a compressor stage in a multiple streams compressor train ([#164](https://github.com/equinor/ecalc/issues/164)) ([ba9235e](https://github.com/equinor/ecalc/commit/ba9235efd01f8b6cfc1dd776f6355d076c3fb93b))
* handle dates in yaml correctly ([e9c28d0](https://github.com/equinor/ecalc/commit/e9c28d057413aa801ec9af86b89f3c4d5b3de8e5))
* issue with crossover rate calculation in system v2 ([#188](https://github.com/equinor/ecalc/issues/188)) ([623a1cf](https://github.com/equinor/ecalc/commit/623a1cfa1e9ee888d69543dc2050cf4c25945baf))
* make ecalc installable again ([58693de](https://github.com/equinor/ecalc/commit/58693debf2cdb774a7b9659214ba9aa9453af8d0))
* rate_type was snake_case in json output ([#172](https://github.com/equinor/ecalc/issues/172)) ([dc82a88](https://github.com/equinor/ecalc/commit/dc82a88930e158fc5b6a762cd1fe7d75534d86d7))
* requested pressures not always an attribute ([#155](https://github.com/equinor/ecalc/issues/155)) ([0078405](https://github.com/equinor/ecalc/commit/0078405e3ad2d254b320239fc8636c3c2bdfbebf))
* system v2 evaluation ([6494257](https://github.com/equinor/ecalc/commit/6494257c5d67f8a19582b2c152d73ec550289196))
* use results base ([#199](https://github.com/equinor/ecalc/issues/199)) ([cebde33](https://github.com/equinor/ecalc/commit/cebde330135210bcc25a5950a2416a8fcf747b09))
* wrongly accessed rate in pump system v2 ([56da4b2](https://github.com/equinor/ecalc/commit/56da4b2a07188200589795ab8a2e7f1ebfe3fe95))


### Documentation

* add further explanation to generic workflow ([ddcb462](https://github.com/equinor/ecalc/commit/ddcb462ba1eda072df2abfd40e95fa677832ef91))
* add generic workflow ([30553e0](https://github.com/equinor/ecalc/commit/30553e0e7282ef35e616d2f3629de57e104d7e42))
* add powerlossfactor in generic workflow ([3d152c8](https://github.com/equinor/ecalc/commit/3d152c880b9d8b33e3ac496ddc96eb2b2f588fb1))
* changelog v8.4 add input compressor pressures to output ([#150](https://github.com/equinor/ecalc/issues/150)) ([46e308f](https://github.com/equinor/ecalc/commit/46e308fba1c1f4001bd1eaa340880c8409c8841b))
* correct order of diagrams ([71a07f5](https://github.com/equinor/ecalc/commit/71a07f5315a28d053557db25209d543d4a570307))
* make mermaid diagram of workflow render correctly ([b1c5b23](https://github.com/equinor/ecalc/commit/b1c5b233907fa705832e55621e6917efb8620df7))
* make mermaid workflow diagram render correctly ([7a99b5b](https://github.com/equinor/ecalc/commit/7a99b5b062804b0f0661ac4d6a62f8d6f32a2fdb))
* update changelog for v8.3 ([b424176](https://github.com/equinor/ecalc/commit/b424176c1dad13f4a29ba7c84cc2354e37b75c2a))
* update workflow with comments ([a71abfe](https://github.com/equinor/ecalc/commit/a71abfe32f02a056a0253ec7e4596b0b10fb94b2))


### Miscellaneous Chores

* add pressure drop ahead of stage to inlet pressure before choking ([#146](https://github.com/equinor/ecalc/issues/146)) ([e5368de](https://github.com/equinor/ecalc/commit/e5368de941febf44f7e5e13c11b1fc3509c2e95d))
* add rate type to compressor model results and convert to time series ([#187](https://github.com/equinor/ecalc/issues/187)) ([c86bf3f](https://github.com/equinor/ecalc/commit/c86bf3f940224ca765f5705f10df676eb6e5d557))
* add validation for missing headers in csv resource file ([#191](https://github.com/equinor/ecalc/issues/191)) ([60e8403](https://github.com/equinor/ecalc/commit/60e84032d932deaf0591c6f5d5d68d70d23dc753))
* adding test of full recirculation in multiple streams compressor trains ([ba9235e](https://github.com/equinor/ecalc/commit/ba9235efd01f8b6cfc1dd776f6355d076c3fb93b))
* calculate correct standard condition density when mixing two streams ([ba9235e](https://github.com/equinor/ecalc/commit/ba9235efd01f8b6cfc1dd776f6355d076c3fb93b))
* clarify neqsim depenedency in ecalc ([#198](https://github.com/equinor/ecalc/issues/198)) ([d6635a9](https://github.com/equinor/ecalc/commit/d6635a988de18799563c09c51ae7f3f7944c8915))
* **docs:** fix equations showing twice ([#141](https://github.com/equinor/ecalc/issues/141)) ([2455e34](https://github.com/equinor/ecalc/commit/2455e34cbaf047bc416a287052c12d9fbbdc963e))
* enable mypy for cli ([#189](https://github.com/equinor/ecalc/issues/189)) ([da713fc](https://github.com/equinor/ecalc/commit/da713fcdac9d2c32ed6b60b788de31a765c1644a))
* fix spelling errors in changelog ([de3c2eb](https://github.com/equinor/ecalc/commit/de3c2eb0cf74068dd6c04e7710eaeb1d2dd27a77))
* remove unnecessary folders ([#186](https://github.com/equinor/ecalc/issues/186)) ([e861d87](https://github.com/equinor/ecalc/commit/e861d8782aa2d3280a7e3e5c24f757558e5656f5))
* rename conflicting file names ([#153](https://github.com/equinor/ecalc/issues/153)) ([654175e](https://github.com/equinor/ecalc/commit/654175e9be0e40b521c6c68871b8a0b85906605c))
* revert nan to num in expressions ([#202](https://github.com/equinor/ecalc/issues/202)) ([2f95c29](https://github.com/equinor/ecalc/commit/2f95c2966ebfc906ebeda2f12ad1fe72ec0a59b4))
* update archive ([#181](https://github.com/equinor/ecalc/issues/181)) ([03abf64](https://github.com/equinor/ecalc/commit/03abf64e9267374b8cd641c09d870631200a2ec5))
* update deps to latest ([0f30f49](https://github.com/equinor/ecalc/commit/0f30f49db6febd033cfd139727c85c31c4676fd2))


### Code Refactoring

* change typ to rate_type for TimeSeriesRate ([#89](https://github.com/equinor/ecalc/issues/89)) ([8be87dd](https://github.com/equinor/ecalc/commit/8be87ddff732592e16ff337fe9927ead438d5928))
* generate asset/ecalc model schema ([#157](https://github.com/equinor/ecalc/issues/157)) ([6818848](https://github.com/equinor/ecalc/commit/6818848afa5f9c390d9214597b8ea938eeb43037))
* generate direct emitter schema ([#180](https://github.com/equinor/ecalc/issues/180)) ([924526a](https://github.com/equinor/ecalc/commit/924526ad7958cfce6e75aa43791224edbcf6db70))
* generate facility type schema ([#182](https://github.com/equinor/ecalc/issues/182)) ([9428979](https://github.com/equinor/ecalc/commit/942897921d8f38115878bdd95349c43c449240b7))
* generate fuel consumer schema ([#160](https://github.com/equinor/ecalc/issues/160)) ([9f580c1](https://github.com/equinor/ecalc/commit/9f580c16f6f25e22d30e8d36dd05536303ec6929))
* generate fuel types schema ([#179](https://github.com/equinor/ecalc/issues/179)) ([e17ef3b](https://github.com/equinor/ecalc/commit/e17ef3be779921e029db5c7ca10ed86a2e71f797))
* generate generator set schema ([#165](https://github.com/equinor/ecalc/issues/165)) ([ab25e05](https://github.com/equinor/ecalc/commit/ab25e055de634a4ecc59ae580834ee2e537fd991))
* generate installation schema ([#159](https://github.com/equinor/ecalc/issues/159)) ([030a44b](https://github.com/equinor/ecalc/commit/030a44baf61719a8de6ed48b772a47eccd7d923c))
* generate time series schema ([#176](https://github.com/equinor/ecalc/issues/176)) ([b02d68d](https://github.com/equinor/ecalc/commit/b02d68dbc615b9802c54d6e9806430aceee1b354))
* improve error message when wrong CURVE-keyword input to single speed compressor ([#173](https://github.com/equinor/ecalc/issues/173)) ([9502bcc](https://github.com/equinor/ecalc/commit/9502bcc8ee504d490e293f4bada839e96e011092))
* improve error message when wrong CURVES-keyword input to variable speed compressor ([#175](https://github.com/equinor/ecalc/issues/175)) ([714e867](https://github.com/equinor/ecalc/commit/714e867f7593527078480e4d9c7bca62da163d7a))
* merge functionality for results ([#193](https://github.com/equinor/ecalc/issues/193)) ([db1e9b1](https://github.com/equinor/ecalc/commit/db1e9b1d52d9dfce48d54dfa6cd77ac4a1bbf92f))
* move common properties for system v2 operational settings ([10b5e07](https://github.com/equinor/ecalc/commit/10b5e07915d52ce6b08f508dd87d31c4d8dc8778))
* move yaml system into package ([b477b15](https://github.com/equinor/ecalc/commit/b477b159cc60df96c5ec230cd8d8db519f721f85))
* remove condition and power_loss_factor from system v2 ([2507bb9](https://github.com/equinor/ecalc/commit/2507bb92730cd4e9b5bd35d2f7e429d493fb5478))
* remove rate_fractions from system v2 ([ba788fd](https://github.com/equinor/ecalc/commit/ba788fdd8dff754c3ca16315d098e00911d91fa0))
* use common Period,Periods classes ([76366ce](https://github.com/equinor/ecalc/commit/76366cec64da5c7585635db69adf457fbb36775e))
* use common to_camel_case function ([#171](https://github.com/equinor/ecalc/issues/171)) ([f5f0c2f](https://github.com/equinor/ecalc/commit/f5f0c2f8da6e07ad666f8fc203876eece646e6e8))
* use yaml prefix for yaml klasses/modules ([#174](https://github.com/equinor/ecalc/issues/174)) ([e91ac2a](https://github.com/equinor/ecalc/commit/e91ac2a77345556d8a53c10a4be049eb8ec2c7ce))

## [8.3.0](https://github.com/equinor/ecalc/compare/v8.2.2...v8.3.0) (2023-08-11)


### ⚠ BREAKING CHANGES

* energy model type not allowed to change over time ([#131](https://github.com/equinor/ecalc/issues/131))

### Features

* output pump head to json-file ([#49](https://github.com/equinor/ecalc/issues/49)) ([60720f4](https://github.com/equinor/ecalc/commit/60720f429cb5da82cd839740eca8d3039c9d5969))


### Bug Fixes

* avoid zero discharge pressure after validation of operational conditions ([830c75e](https://github.com/equinor/ecalc/commit/830c75e27a29549157658c606e618da381c24e81))
* bug fix to joining results from different temporal models with compressor train models having multiple inlet or outlet streams ([#63](https://github.com/equinor/ecalc/issues/63)) ([da3144a](https://github.com/equinor/ecalc/commit/da3144a0cbb3e6121809c8eeee86e62a2a3ed5e1))
* json schema accepts MAXIMUM_DISCHARGE_PRESSURE for single speed train ([#86](https://github.com/equinor/ecalc/issues/86)) ([a18de1e](https://github.com/equinor/ecalc/commit/a18de1eae60085211b640b67a4f372346382fdc8))
* json schema allow stages to have control_margin and control_margin_unit ([#90](https://github.com/equinor/ecalc/issues/90)) ([2415534](https://github.com/equinor/ecalc/commit/2415534053df4e50496fd2ae4504cff76ab14346))
* make apply_condition work for 2D numpy arrays also ([#78](https://github.com/equinor/ecalc/issues/78)) ([bce91cb](https://github.com/equinor/ecalc/commit/bce91cb0b6b821e1b1a579c40f19311e847577b3))
* make sure that suction pressure is less than or equal to discharge pressure for compressor train ([#104](https://github.com/equinor/ecalc/issues/104)) ([d218273](https://github.com/equinor/ecalc/commit/d2182730c2fdcd98e54fef8625cd289dc206b2bf))
* parse scientific notation numbers in expression ([#85](https://github.com/equinor/ecalc/issues/85)) ([fdf322b](https://github.com/equinor/ecalc/commit/fdf322bafa9a3379b6481e57ca1e761475f42b25))
* parse spaces as thousand separators from excel ([#107](https://github.com/equinor/ecalc/issues/107)) ([5a3bd6a](https://github.com/equinor/ecalc/commit/5a3bd6a2b8e85dcc248435b30677e278d64c7f93))
* pump results wrong when resampled ([#71](https://github.com/equinor/ecalc/issues/71)) ([daffdb3](https://github.com/equinor/ecalc/commit/daffdb3d969add106bbbfd782cfae418cfd8650d))
* resample emissions correctly to create valid json ([3c9b52e](https://github.com/equinor/ecalc/commit/3c9b52e40c1c88a11db3d088c0fbb320a4920daa))
* result of validation of operational conditions when rate is zero should always be valid ([9de403c](https://github.com/equinor/ecalc/commit/9de403c8b92895fafabea875d970fc1901a4ba89))
* validate time steps where rate is different from zero, not only when larger than zero ([6ce07c4](https://github.com/equinor/ecalc/commit/6ce07c41e82b397d9512566a42fd8fd2017c14d1))
* wrong standard_conditions_density when mixing two fluids ([a16a695](https://github.com/equinor/ecalc/commit/a16a695736125dc4b662ab31ab9a83186b14f369))


### Documentation

* fix generic compressor example ([38870a3](https://github.com/equinor/ecalc/commit/38870a3f735e7397502345dda69f646240328490))
* fix links ([#116](https://github.com/equinor/ecalc/issues/116)) ([62cadfc](https://github.com/equinor/ecalc/commit/62cadfcf581b101d7bb33b3772ffb65eefbf670b))
* how to migrate from 8.1 to 8.2 ([4d3be58](https://github.com/equinor/ecalc/commit/4d3be58f5af44cbdee4158017b163361371dc23c))
* remove unnecessary information from migration guide ([4730538](https://github.com/equinor/ecalc/commit/47305386db82d826245c67e6c10a8597a36bfc09))
* specify only gensets for boiler/heater ([#53](https://github.com/equinor/ecalc/issues/53)) ([2df3bdf](https://github.com/equinor/ecalc/commit/2df3bdf299bcb6cf47289259e4fedd21c2de141c))
* update changelog 8.2 with changes for ltp- and stp ([#43](https://github.com/equinor/ecalc/issues/43)) ([6fe4b77](https://github.com/equinor/ecalc/commit/6fe4b773a156d01eec67e8e70b764d4e18d374ce))
* update changelog for 8.2 ([3ccea74](https://github.com/equinor/ecalc/commit/3ccea743332f0d1950ff61ca6747bb507ea37bd4))
* update docs and changelog for energy models ([#133](https://github.com/equinor/ecalc/issues/133)) ([8f0d716](https://github.com/equinor/ecalc/commit/8f0d71633d80a99da369dffa05f386e554f3c0bb))
* update documentation for heaters and boilers ([#52](https://github.com/equinor/ecalc/issues/52)) ([2bef707](https://github.com/equinor/ecalc/commit/2bef70731be94ace7d0a2269f2ebf07bd01e82b2))
* update migration guide with ltp- and stp changes ([#42](https://github.com/equinor/ecalc/issues/42)) ([4b0b230](https://github.com/equinor/ecalc/commit/4b0b23011a9d2161741dd52031070307fc6c1b68))


### Miscellaneous Chores

* add 8.3 changelog ([9f4a4af](https://github.com/equinor/ecalc/commit/9f4a4af545126922a38807c51268bd84dfb868db))
* add fluid mixing checks ([53c1626](https://github.com/equinor/ecalc/commit/53c1626ebf10edc71c0ba4ef5fcdbe1cd6a32ac0))
* add fluid mixing checks ([0f3ddca](https://github.com/equinor/ecalc/commit/0f3ddcaca1164acad3f5d213b2e8daac05333042))
* add installation filter to flare nmvoc ([#87](https://github.com/equinor/ecalc/issues/87)) ([f37b76d](https://github.com/equinor/ecalc/commit/f37b76d0b3c2f6941585299998205c3a907b41a8))
* add installation filter to remaining ltp-columns ([#91](https://github.com/equinor/ecalc/issues/91)) ([39df792](https://github.com/equinor/ecalc/commit/39df7923d79a393981285986016311e9f1b0848f))
* add power adjustment constant also for compressor trains with interstage pressure ([#136](https://github.com/equinor/ecalc/issues/136)) ([c8a4861](https://github.com/equinor/ecalc/commit/c8a486114ec713358798a5dba2a5500dfbbef21d))
* add test for adjust energy usage on multiple streams and pressures compressor trains ([c8a4861](https://github.com/equinor/ecalc/commit/c8a486114ec713358798a5dba2a5500dfbbef21d))
* add test of count_parentheses ([0d1ce6f](https://github.com/equinor/ecalc/commit/0d1ce6feff7a6aaeecab57fd9a661122b691d3b5))
* add test of validation of operational conditions when suction pressure exceeds discharge pressure ([d218273](https://github.com/equinor/ecalc/commit/d2182730c2fdcd98e54fef8625cd289dc206b2bf))
* added changelog entry about interstage pressure fix ([#95](https://github.com/equinor/ecalc/issues/95)) ([2a1e8b0](https://github.com/equinor/ecalc/commit/2a1e8b085ed87dcbb8da874b64f737721f0ceaae))
* count parentheses in list of tokens only among the elements that are strings ([#94](https://github.com/equinor/ecalc/issues/94)) ([0d1ce6f](https://github.com/equinor/ecalc/commit/0d1ce6feff7a6aaeecab57fd9a661122b691d3b5))
* energy model type not allowed to change over time ([#131](https://github.com/equinor/ecalc/issues/131)) ([670cff2](https://github.com/equinor/ecalc/commit/670cff2154e2881aea25903557a7f187bdab05ee))
* enforce unique fuel type names, and unique emission names within one fuel type ([#84](https://github.com/equinor/ecalc/issues/84)) ([4ea9c63](https://github.com/equinor/ecalc/commit/4ea9c630510015e2030f0840b933ea399cc0734b))
* fix broken link in documentation of GENERATORSETS keyword ([#103](https://github.com/equinor/ecalc/issues/103)) ([329c8e9](https://github.com/equinor/ecalc/commit/329c8e993c217e7685c082b7671a12c4115bba87))
* fix typing of fluid composition ([c0d98b3](https://github.com/equinor/ecalc/commit/c0d98b3a6f4dfb411edfa9bdd8be3c887b28f6da))
* improve documentation on defining compressor charts using CURVE and CURVES ([#97](https://github.com/equinor/ecalc/issues/97)) ([1bde68a](https://github.com/equinor/ecalc/commit/1bde68a38e75255c8f2d6cd88fb5b6ba1ddb97c9))
* improve error message when bad yaml file name ([#77](https://github.com/equinor/ecalc/issues/77)) ([d2eb733](https://github.com/equinor/ecalc/commit/d2eb733264b2d5b2114a785096c9d6abbffea21b))
* merge queue ([d4489c6](https://github.com/equinor/ecalc/commit/d4489c604b807c07a7e41a038cbdfeca9720ade1))
* numpy ndarray typing ([#46](https://github.com/equinor/ecalc/issues/46)) ([9b7b308](https://github.com/equinor/ecalc/commit/9b7b308ea6ce5c0aee5acdf8226cd94b90b448aa))
* pin numpy to compatible numpy version ([35a3640](https://github.com/equinor/ecalc/commit/35a3640a96c376f4d37e74fd62aec0f0a0bf458b))
* remove limiting dependency typer-cli ([8208444](https://github.com/equinor/ecalc/commit/820844475c29460f29a44bb7917ed5bd37d4ad45))
* simplify dependencies for use with komodo ([39c5c36](https://github.com/equinor/ecalc/commit/39c5c365aea85ba333a5a509fe5cfbee1be5d9d0))
* update dependencies to be aligned with external requirements ([fbfbfeb](https://github.com/equinor/ecalc/commit/fbfbfeb4292011c04d9107218a5b4188e052f7ff))
* update snapshots after power adjustment constant fix for compressor trains with interstage pressure ([c8a4861](https://github.com/equinor/ecalc/commit/c8a486114ec713358798a5dba2a5500dfbbef21d))


### Code Refactoring

* consumer system v2 ([248dabb](https://github.com/equinor/ecalc/commit/248dabb595a12ed6ca9a0f8ef519f5439a3b0964))
* ensure neqsim fluid is contained to FluidStream object ([#118](https://github.com/equinor/ecalc/issues/118)) ([d1d6ad6](https://github.com/equinor/ecalc/commit/d1d6ad6fa1c6cfdf4eee428477995c6f163fa11a))
* enthalpy calculations ([#109](https://github.com/equinor/ecalc/issues/109)) ([a01a215](https://github.com/equinor/ecalc/commit/a01a2153fe904d191150c4ced09257dc45484194))
* enthalpy calculations ([#110](https://github.com/equinor/ecalc/issues/110)) ([cf7d1a9](https://github.com/equinor/ecalc/commit/cf7d1a9e975fece41b98f4ab6c7bbb3edb562735))
* improve naming and documentation ([94be7fa](https://github.com/equinor/ecalc/commit/94be7fa714a0db20944e9b35d1867d11a0748e7f))
* molar_mass_kg_per_mol is not used in the code ([3ea535e](https://github.com/equinor/ecalc/commit/3ea535ef68ead2b600b33319c1ed70907e7ba681))
* move NeqSimfluid creation into NeqSim wrapper ([57c4b24](https://github.com/equinor/ecalc/commit/57c4b244d6449c6b43bcea75a1f7ed1f82ccfc8c))
* NeqSim mapping ([#120](https://github.com/equinor/ecalc/issues/120)) ([0a0b2fe](https://github.com/equinor/ecalc/commit/0a0b2fea564c1695bb920145086f23bccac91528))
* remove FluidStream copy ([#119](https://github.com/equinor/ecalc/issues/119)) ([0e30ab2](https://github.com/equinor/ecalc/commit/0e30ab288b18fecbde62067564ac235d6c58dae1))
* Use a list comprehension to create a transformed list ([#112](https://github.com/equinor/ecalc/issues/112)) ([5d7292b](https://github.com/equinor/ecalc/commit/5d7292bdafd16bc74b2e9b8bc13e97cf279fd9f7))


### Tests

* add test for fluid stream mixing ([0ba8f8f](https://github.com/equinor/ecalc/commit/0ba8f8fff9503b791b6edaf16c45cb3d922d6c2b))


### Continuous Integration

* create release-please pr against correct branch ([be9426a](https://github.com/equinor/ecalc/commit/be9426a774b8704b2f22e9a83544e07bd92a8808))
* fix issue with api reference docs generation ([#44](https://github.com/equinor/ecalc/issues/44)) ([42c1402](https://github.com/equinor/ecalc/commit/42c140269a9e8a6d5f09e9354d14ae51d02f3e81))
* fix syntax for gh action workflow ([d8700dd](https://github.com/equinor/ecalc/commit/d8700dd9bccd40cb4b3bdb75119e0bd47baf3985))
* Lock pydantic version in CI and update hooks ([#106](https://github.com/equinor/ecalc/issues/106)) ([2ea517e](https://github.com/equinor/ecalc/commit/2ea517e79a34195e561a4897798bd24ef9cae6ae))
* remove duplicate build of docs ([#62](https://github.com/equinor/ecalc/issues/62)) ([e5b896b](https://github.com/equinor/ecalc/commit/e5b896b9f46a7e13c6d806237c4d4bef44833b77))
* set default ownership for source ([16d54f1](https://github.com/equinor/ecalc/commit/16d54f1a30368d92ead377baceef98820754c25f))
* support hotfix releases ([0346929](https://github.com/equinor/ecalc/commit/03469295d20526e391938a5830d1513088a8803f))
* update pre-commit settings ([6092255](https://github.com/equinor/ecalc/commit/6092255da9ca373537b162b21190bfe9f138a027))

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
