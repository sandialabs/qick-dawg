## [1.2.1](https://github.com/sandialabs/qick-dawg/compare/v1.2.0...v1.2.1) (2025-01-29)


### Bug Fixes

* fixed installation to remove qd install and paths ([033c254](https://github.com/sandialabs/qick-dawg/commit/033c254772d211be45b8f4bffe012e33bde48643))



# [1.2.0](https://github.com/sandialabs/qick-dawg/compare/v1.1.0...v1.2.0) (2025-01-17)


### Features

* **photon_counting:** confirmed photon counting works for all pulse sequences ([8b2b19b](https://github.com/sandialabs/qick-dawg/commit/8b2b19be11afb0ecf28463a3fcdd160128649500))



# [1.1.0](https://github.com/sandialabs/qick-dawg/compare/v1.0.2...v1.1.0) (2025-01-15)


### Bug Fixes

* changed analysis to consistently have contrast as just the difference ([99f3689](https://github.com/sandialabs/qick-dawg/commit/99f3689193fd52b401bf3cee09f1952e2b7336fa))
* **client:** fixed start client for remote use ([da3c227](https://github.com/sandialabs/qick-dawg/commit/da3c2276c963aa9c76bbd9d7c68178ad4ae74255))
* fixing integration of photon counting with newest version ([2b2b561](https://github.com/sandialabs/qick-dawg/commit/2b2b561c756487008b7e4c56eef0b44696a88c99))
* **graphics:** fixed the graphics path error ([a0bd964](https://github.com/sandialabs/qick-dawg/commit/a0bd96457cf18ea79692b7e475bb2adfe1770714))
* **install:** added itemattribute to the requirements list ([ea95c23](https://github.com/sandialabs/qick-dawg/commit/ea95c23445867eadc1b8c0477992633d63e7c3c2))
* **installation:** simplified package installation, only supporting online installs ([7989c24](https://github.com/sandialabs/qick-dawg/commit/7989c249ffe6b410dbbd6b7fa39e393d4a25b44a))
* **itemattribute:** used pypi itemattribute with correct item assignment ([9279638](https://github.com/sandialabs/qick-dawg/commit/9279638c9bc8ed6e4b199c472c506f9e55cb58db))
* **pulsing:** small pulsing changes with integrated ddr4 and testing ([1243e80](https://github.com/sandialabs/qick-dawg/commit/1243e80d6f1d9627afd71e34390caa14125c4dba))
* **t1:** swapped pulsing order for consistent analysis ([6cadb08](https://github.com/sandialabs/qick-dawg/commit/6cadb082b20df814686d5ce70dc8401c4769297c))
* updated qick version requirement to include remote fix ([bfb8c05](https://github.com/sandialabs/qick-dawg/commit/bfb8c05bb2530416193ddb9f0598999db0bcc4aa))


### Features

* added NVAverageprogram.setup_readout to setup analog or digital readout ([f63008a](https://github.com/sandialabs/qick-dawg/commit/f63008a0d3586949d7d911eefccbc9332204a8c1))
* added simple read out window to calibrate photon ttl levels ([1518307](https://github.com/sandialabs/qick-dawg/commit/1518307846dac81afcc4606da0b73067339839df))
* added simple read out window to calibrate photon ttl levels ([a73505e](https://github.com/sandialabs/qick-dawg/commit/a73505e80e438c17fc321d48ae5deafeb4cdf8a2))
* **client:** Added local mode to start client ([e9121ee](https://github.com/sandialabs/qick-dawg/commit/e9121ee119d2ba81568bd14a6e318cfa29ad14a1))
* **cpmgxy8:** Added cpmgxy8, delay sweep demonstrated ([b361e42](https://github.com/sandialabs/qick-dawg/commit/b361e42a9190cae5599c9dfe2a913e920fce82f1))
* Lockin-ODMR now has counting mode and analyze digital or analog ([d1f25c1](https://github.com/sandialabs/qick-dawg/commit/d1f25c1bb5800fba44cf702ecb164f1e4864daf2))
* PLIntensity now works with edge counting, analysis can be rate or total ([95c3447](https://github.com/sandialabs/qick-dawg/commit/95c34478b1f7bb7e3624fb21d4c7f24681c056ff))
* updated laser on/off to read out single TTLs from edge counting mode ([9e979d9](https://github.com/sandialabs/qick-dawg/commit/9e979d997c2af625dfaef0ec865570041c5ba267))



## [1.0.2](https://github.com/sandialabs/qick-dawg/compare/v1.0.1...v1.0.2) (2024-12-18)


### Bug Fixes

* **pulse_readout:** pulse readout end was slightly off ([68eb37b](https://github.com/sandialabs/qick-dawg/commit/68eb37bbc09b0becce2c9c51757ab560665bcc9a))
* **rabi:** fixed rabi sequence, dropped 'length' syntax ([bdb7407](https://github.com/sandialabs/qick-dawg/commit/bdb7407917c73408db28b36c23d1107017f970ad))
* **readoutwindow:** modified readoutwindow so that it doesn't use sycnall ([b1bdc86](https://github.com/sandialabs/qick-dawg/commit/b1bdc86db1e95ef05f6c863b5a5d07347a42a6c7))



## [1.0.1](https://github.com/sandialabs/qick-dawg/compare/v0.0.6...v1.0.1) (2024-10-12)


### Bug Fixes

* **meta:** fixed import so it's no longer broken ([98db853](https://github.com/sandialabs/qick-dawg/commit/98db853614c61325841e4fc83b7cc3555bbff4d5))
* **meta:** fixed import so it's no longer broken ([#47](https://github.com/sandialabs/qick-dawg/issues/47)) [skip ci] ([4c4ef57](https://github.com/sandialabs/qick-dawg/commit/4c4ef57527fa38b323606968fb581aa23d2860ff))



## [0.0.6](https://github.com/sandialabs/qick-dawg/compare/v0.2.0...v0.0.6) (2024-10-09)


### Bug Fixes

* **init:** updated init message ([efe2b00](https://github.com/sandialabs/qick-dawg/commit/efe2b0069b64a1edfb3cd989c3ddffb5b6a658fa))
* **meta:** changed convetional commits and corrected errors for autotesting: ([677d035](https://github.com/sandialabs/qick-dawg/commit/677d0355731042d4142a0ed91cc9e24716fe7648))
* **pyproject:** fixed missing quote ([74d003c](https://github.com/sandialabs/qick-dawg/commit/74d003cbac645499a1f91a53a4684f74488ca458))
* started to fix NVAverager Program ([a01aa6e](https://github.com/sandialabs/qick-dawg/commit/a01aa6e1859e35dda76d260663103359143b7715))
* **upgrade qick:** upgraded to qick 0.2.289. BREAKING CHANGE ([ebd083b](https://github.com/sandialabs/qick-dawg/commit/ebd083bbd998da5d6e7d683302d700ed3c51e693))



