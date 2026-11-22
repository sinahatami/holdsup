# Changelog

## [0.8.0](https://github.com/sinahatami/holdsup/compare/v0.7.0...v0.8.0) (2026-11-22)


### Features

* **web:** one-minute teaser video in "How it works", plus make e2e-ui and lighthouse-ui ([#101](https://github.com/sinahatami/holdsup/issues/101)) ([08ed4b8](https://github.com/sinahatami/holdsup/commit/08ed4b8a501762264dfd0ad1521aaa90fe388482))


### Performance Improvements

* **web:** a result page paints half a second sooner: two font preloads, live-check code on demand, one logo path ([#99](https://github.com/sinahatami/holdsup/issues/99)) ([7e33e98](https://github.com/sinahatami/holdsup/commit/7e33e9811c2551a9d2894d6fe7ddfb42b6a04e8c))
* **web:** lay out below-the-fold sections only when scrolled near ([#102](https://github.com/sinahatami/holdsup/issues/102)) ([0a205a4](https://github.com/sinahatami/holdsup/commit/0a205a4c6888bb98c085fffb7a64b3062a888230))

## [0.7.0](https://github.com/sinahatami/holdsup/compare/v0.6.0...v0.7.0) (2026-11-21)


### Features

* privacy and terms page, claim-box notice, and private removal requests ([#95](https://github.com/sinahatami/holdsup/issues/95)) ([8097101](https://github.com/sinahatami/holdsup/commit/8097101cc9f119fc9b7c8c26687eb6c8de594fe6))
* **web:** share a check from one row, with the other ways behind "More ways" ([#98](https://github.com/sinahatami/holdsup/issues/98)) ([af724af](https://github.com/sinahatami/holdsup/commit/af724af6c389fae373c40cb5c978365574fc2807))
* **web:** tooltips, back-to-top, share tabs, receipt heading and live progress (6 commits) ([#96](https://github.com/sinahatami/holdsup/issues/96)) ([37bc789](https://github.com/sinahatami/holdsup/commit/37bc78970935060d4ea3902101e84313a08e519c))

## [0.6.0](https://github.com/sinahatami/holdsup/compare/v0.5.0...v0.6.0) (2026-11-21)


### ⚠ BREAKING CHANGES

* GET /v1/eval and the /eval page are removed.
* remove the status page; show the release version in the footer ([#88](https://github.com/sinahatami/holdsup/issues/88))

### Features

* remove the eval page and GET /v1/eval ([#92](https://github.com/sinahatami/holdsup/issues/92)) ([3c061cf](https://github.com/sinahatami/holdsup/commit/3c061cf3af0b8136beb39fb59fee53e5cfc16a4b))
* remove the status page; show the release version in the footer ([#88](https://github.com/sinahatami/holdsup/issues/88)) ([0b90710](https://github.com/sinahatami/holdsup/commit/0b90710fb39e770f64b827e401a0395b96ddb2ce))
* **web:** canonical links, og:url and a Search Console tag ([#91](https://github.com/sinahatami/holdsup/issues/91)) ([421e3f4](https://github.com/sinahatami/holdsup/commit/421e3f45bb53c9d0f2d71161f6382b9439f4694b))

## [0.5.0](https://github.com/sinahatami/holdsup/compare/v0.4.2...v0.5.0) (2026-11-20)


### Features

* **deploy:** run the API on Google Cloud Run instead of a Hugging Face Space ([#77](https://github.com/sinahatami/holdsup/issues/77)) ([28fbd70](https://github.com/sinahatami/holdsup/commit/28fbd70bd4b9ed5cd765e466806f835bac8c9c98))


### Bug Fixes

* judge the smoke gate claim by claim, and leave one-year windows out of the start-and-end check ([#78](https://github.com/sinahatami/holdsup/issues/78)) ([493450b](https://github.com/sinahatami/holdsup/commit/493450bde88f12b40353dd660b2032829a2d9831))


### Performance Improvements

* **api:** one query for /status, gzip JSON, and run next to the database ([#81](https://github.com/sinahatami/holdsup/issues/81)) ([87a613e](https://github.com/sinahatami/holdsup/commit/87a613e5f12b86e47d633c7aa514ef0e97b08515))
* **web:** cut Newsreader to the weights and sizes the site sets ([#80](https://github.com/sinahatami/holdsup/issues/80)) ([b71cc15](https://github.com/sinahatami/holdsup/commit/b71cc15d46b69726441b97760df35afd220db8a4))
* **web:** keep server-only text out of browser bundles; add robots.txt and a sitemap ([#82](https://github.com/sinahatami/holdsup/issues/82)) ([346978a](https://github.com/sinahatami/holdsup/commit/346978ac6f34db453e459d65a7e3fcfccae26c75))

## [0.4.2](https://github.com/sinahatami/holdsup/compare/v0.4.1...v0.4.2) (2026-11-20)


### Bug Fixes

* **api:** make the API image deployable and its rate limits unforgeable ([#74](https://github.com/sinahatami/holdsup/issues/74)) ([1e2f921](https://github.com/sinahatami/holdsup/commit/1e2f921a09885037a5a7be1238a00da22b6c2bae))

## [0.4.1](https://github.com/sinahatami/holdsup/compare/v0.4.0...v0.4.1) (2026-11-20)


### Bug Fixes

* a level claim answered with two values is read at the claim's end ([#70](https://github.com/sinahatami/holdsup/issues/70)) ([bbcf4e2](https://github.com/sinahatami/holdsup/commit/bbcf4e228eecfe7163e38721f73a057ea4dfdc0a))

## [0.4.0](https://github.com/sinahatami/holdsup/compare/v0.3.0...v0.4.0) (2026-11-20)


### Features

* claim watch re-checks stored claims when a source revises its figures (S1) ([#67](https://github.com/sinahatami/holdsup/issues/67)) ([b01d1c3](https://github.com/sinahatami/holdsup/commit/b01d1c3c1331534b1a09d68088b7f88ba8a0845c))


### Bug Fixes

* the claim watch follows a featured cached copy into the gallery ([#69](https://github.com/sinahatami/holdsup/issues/69)) ([894e264](https://github.com/sinahatami/holdsup/commit/894e264a0f465031af6405e75887a8d5328cd799))

## [0.3.0](https://github.com/sinahatami/holdsup/compare/v0.2.0...v0.3.0) (2026-11-20)


### Features

* check an article from its link (S3) ([#65](https://github.com/sinahatami/holdsup/issues/65)) ([81a2c9c](https://github.com/sinahatami/holdsup/commit/81a2c9c2c5ff63bce48e934185ecb848d9306e2a))

## [0.2.0](https://github.com/sinahatami/holdsup/compare/v0.1.0...v0.2.0) (2026-11-19)


### Features

* **web:** embeddable verdict widget (S2) ([#61](https://github.com/sinahatami/holdsup/issues/61)) ([2ed25c3](https://github.com/sinahatami/holdsup/commit/2ed25c33c58c3a8773376ee325744c9e6dd18ee7))
* **web:** new HoldsUp logo, Newsreader type and paper share cards ([#63](https://github.com/sinahatami/holdsup/issues/63)) ([24bf7de](https://github.com/sinahatami/holdsup/commit/24bf7deea9bdec2c19ee5dcd3fe73c697205e006))

## 0.1.0 (2026-11-19)


### Features

* add API Dockerfile, Alembic with pgvector, Vercel and keep-alive configs ([15640ed](https://github.com/sinahatami/holdsup/commit/15640ed0884dbfcdcf7686df6dced7721905b002))
* add Eurostat adapter with JSON-stat 2.0 decoder and fixtures ([18e0beb](https://github.com/sinahatami/holdsup/commit/18e0beb52aef453967bbb2d8931ac6ef9a6b54c4))
* add indicator catalog with validation, embeddings, and vector search ([9525c67](https://github.com/sinahatami/holdsup/commit/9525c674fb4c262ddb289c841f0b911ea2a369fa))
* add model router with budgets, cool-downs and circuit breaker ([b6dacde](https://github.com/sinahatami/holdsup/commit/b6dacdef079d26167e0c14676f4479f9cdd488b1))
* add pivot test script and change op ([2c1a9c4](https://github.com/sinahatami/holdsup/commit/2c1a9c449285f721eea5ac9b5cab875376b05e27))
* add provider smoke script for JSON-schema and tool calls ([ac5f845](https://github.com/sinahatami/holdsup/commit/ac5f84565b2728114f8a984ca293590290a620f9))
* add World Bank and OWID adapters with a 24-hour series cache ([2f900b5](https://github.com/sinahatami/holdsup/commit/2f900b5171881225b82db7f02acf0f9e8a46da52))
* **api:** add the check endpoints, live SSE trace, results tables and per-IP limit ([3696e9e](https://github.com/sinahatami/holdsup/commit/3696e9e0b138607f3c383f916746c2bc9438fb05))
* **api:** add the gallery seeding script and curated claims ([fec5e50](https://github.com/sinahatami/holdsup/commit/fec5e50f7b9ba227aea6e8cad02d691da5996672))
* **api:** change points, and a start or end that carries the claim (P3.3) ([f7fd377](https://github.com/sinahatami/holdsup/commit/f7fd377b25ad923c5bee3dabc2b90b293f8b0686))
* **api:** check a trend's start and end for a peak, a trough or a break ([#47](https://github.com/sinahatami/holdsup/issues/47)) ([682ed51](https://github.com/sinahatami/holdsup/commit/682ed518a46ac7445b882513886413aeb50bde10))
* **api:** distortion checks (P3.4) ([897aa8f](https://github.com/sinahatami/holdsup/commit/897aa8feb0f1918cfc239525fe928f076c27fc5c))
* **api:** fall back to GPT-OSS 120B on Cerebras when Groq is out ([#43](https://github.com/sinahatami/holdsup/issues/43)) ([169b84a](https://github.com/sinahatami/holdsup/commit/169b84a6aeb8fd96b734ac2f9f9de59fd50fbe14))
* **api:** give each gallery item its claims, with the figures they were checked against ([9e902a3](https://github.com/sinahatami/holdsup/commit/9e902a35de2f767ef86fc8cedbe16a6ebbf09e32))
* **api:** make missing-report lists the topics most often can't-checked ([b81d300](https://github.com/sinahatami/holdsup/commit/b81d3004b94d2894a37481fdbdf64db3e11925f7))
* **api:** ops for the age of a figure and a price index from inflation ([a9725aa](https://github.com/sinahatami/holdsup/commit/a9725aa91affc8a67ff37709193abd3af52a5c67))
* **api:** read half-year periods (2024-S1, 2024-S2) end to end ([cf08208](https://github.com/sinahatami/holdsup/commit/cf08208e0626307bc81897f128606670df46f06c))
* **api:** record readers' reports of a wrong match ([21ff60b](https://github.com/sinahatami/holdsup/commit/21ff60b7a35f80ef45a4e0c485e7fd2009dd40aa))
* **api:** record the step a claim stopped at ([8011af0](https://github.com/sinahatami/holdsup/commit/8011af03ed3860429799532bf5d624c606933cc0))
* **api:** the cherry-pick sweep over every time window (P3.1) ([f0a3719](https://github.com/sinahatami/holdsup/commit/f0a37193595920fe700349ec078c78d8600297cb))
* **api:** the receipt as a notebook that replays every calculation (P3.6) ([fdccae1](https://github.com/sinahatami/holdsup/commit/fdccae140830727c2404ed64c4d280636ebf2a8b))
* **api:** the series each claim's answer read (P3.5) ([05a4895](https://github.com/sinahatami/holdsup/commit/05a48956f606eecd9af4ce59a5d0baee7f45246f))
* **api:** total population as the per-capita denominator, plain can't-check messages ([d442932](https://github.com/sinahatami/holdsup/commit/d442932658b1eb23d5bd49b30dbd762e4afe73be))
* **catalog:** add 45 indicators across nine themes (catalog 0.6.0) ([258395e](https://github.com/sinahatami/holdsup/commit/258395eb06547fc3651df5594979558bcc7058e8))
* **catalog:** add aliases to 31 indicator entries and publish them from drafts ([92e6d31](https://github.com/sinahatami/holdsup/commit/92e6d31dd32b0ebc7d3a019ae0d24ad1beb4f49b))
* **catalog:** household electricity price and minimum wage in euro (catalog 0.7.0) ([dcb9fc7](https://github.com/sinahatami/holdsup/commit/dcb9fc7516f33ec80dde9d7b895d02ca4e8a2168))
* **catalog:** mark money at current prices and its real version (0.8.0) ([479cc29](https://github.com/sinahatami/holdsup/commit/479cc29edb7814fa30d353b0e46719f12aa48a65))
* **eval:** replay saved model replies by default in make eval and eval-smoke ([#47](https://github.com/sinahatami/holdsup/issues/47)) ([682ed51](https://github.com/sinahatami/holdsup/commit/682ed518a46ac7445b882513886413aeb50bde10))
* evaluation runner, make eval-smoke and the CI smoke job (P4.2) ([#31](https://github.com/sinahatami/holdsup/issues/31)) ([ea39a01](https://github.com/sinahatami/holdsup/commit/ea39a01ec31ef0256d5b18005707c4e98ccd1f18))
* head-to-head baseline and the /eval page (P4.6) ([#42](https://github.com/sinahatami/holdsup/issues/42)) ([5f97c9e](https://github.com/sinahatami/holdsup/commit/5f97c9e05808be9beb354dd83c5edef87daac82f))
* how sure each verdict is, and holding back the unsure ones (P4.5) ([#39](https://github.com/sinahatami/holdsup/issues/39)) ([782ef4f](https://github.com/sinahatami/holdsup/commit/782ef4f78a158065391d6f6e527d0e05a91ee1f1))
* **ml:** indicator reranker training, cross-validated on the dev split (P4.3) ([#32](https://github.com/sinahatami/holdsup/issues/32)) ([6adf50c](https://github.com/sinahatami/holdsup/commit/6adf50ce7d7e03c81f766d4e61ff88c63cf42616))
* **ops:** add the eight safe analysis operations with records and flags ([1c398ac](https://github.com/sinahatami/holdsup/commit/1c398ac75828914a0b617ccd68e394f5e07b23bc))
* Phase 3 — series charts, framing checks, notebooks, re-checks, status (P3.4–P3.7) ([#30](https://github.com/sinahatami/holdsup/issues/30)) ([5571cf5](https://github.com/sinahatami/holdsup/commit/5571cf565e2bb4cd383c28d519833c73628eb2f2))
* **pipeline:** add the analysis planning step and deterministic verdict rules ([75ce020](https://github.com/sinahatami/holdsup/commit/75ce0206f2daa94cce3f03fdcdd0d510cbc8f33e))
* **pipeline:** add the claim extraction step with ClaimSpec ([ee0772c](https://github.com/sinahatami/holdsup/commit/ee0772c1b4a0b47bbd97d4cf6a88f766de8a7be5))
* **pipeline:** add the explanation step with the invented-number check, and the claim ledger ([37c7eea](https://github.com/sinahatami/holdsup/commit/37c7eea90e976044e35b42acd9381575c14b41be))
* **pipeline:** add the indicator matching step ([43f1c2f](https://github.com/sinahatami/holdsup/commit/43f1c2fda210652c7d946e4581163b2b16ec3efe))
* **pivot:** save model steps and add --refetch; record the first full run ([d5ed0af](https://github.com/sinahatami/holdsup/commit/d5ed0af898761548582fe73ba43c7b631ea20356))
* restore P1.4–P1.9 and add pivot test script (P1.11) ([457e9f8](https://github.com/sinahatami/holdsup/commit/457e9f8d5b448c302b963a6c2b617e2bb61e9016))
* scaffold monorepo with FastAPI health route and Next.js home page ([20264c2](https://github.com/sinahatami/holdsup/commit/20264c2da9689c6cfa6592c11a6282c63de423e4))
* the reranker in matching, with the skip-the-model rule (P4.4) ([#37](https://github.com/sinahatami/holdsup/issues/37)) ([23dc3f5](https://github.com/sinahatami/holdsup/commit/23dc3f5704cdbd43313c0a24f1dbe5b53b6337fc))
* **web:** a chart of the data over time on each claim (P3.5) ([f1ab1e0](https://github.com/sinahatami/holdsup/commit/f1ab1e06dfc08b45c7bb8128b2fad646c9802385))
* **web:** a Lighthouse budget in CI, and a bundle analyzer ([c879c33](https://github.com/sinahatami/holdsup/commit/c879c33fca2ecb8e4684485f56c81d7fc031a2e1))
* **web:** a Lighthouse budget in CI, and a layout-shift fix on the check page ([2b5dae5](https://github.com/sinahatami/holdsup/commit/2b5dae53d0b5dc7029c1c30644f3a24cfb758e3c))
* **web:** a shorter footer in two groups, with the licence and a way to report a problem ([dd407e3](https://github.com/sinahatami/holdsup/commit/dd407e3b3d64dde372d7c8d575bae10af5794754))
* **web:** a shorter methodology page, with the working folded away ([231585b](https://github.com/sinahatami/holdsup/commit/231585bf368b8079e06813c7289b6cfc86170498))
* **web:** add an About page with how to add a statistic ([82e9044](https://github.com/sinahatami/holdsup/commit/82e90440eb2f7583821c2c54c72a6985117c154a))
* **web:** add site header and footer, theme toggle, how-it-works, 404 page and refreshed styling ([98eeea4](https://github.com/sinahatami/holdsup/commit/98eeea4a11b0c7f114808c05f6d89a4300fc75f0))
* **web:** add the home page, live result page, verdict, trace and basic receipt ([299abc9](https://github.com/sinahatami/holdsup/commit/299abc9e399049d7ef20325b32b626b3352b4b19))
* **web:** an at-capacity state with checks to read while it waits (P5.1) ([#48](https://github.com/sinahatami/holdsup/issues/48)) ([0e61dc3](https://github.com/sinahatami/holdsup/commit/0e61dc3247e2f02d4e5e7bc65917bd470ab820f3))
* **web:** calm the background and make the wordmark a solid colour ([b984536](https://github.com/sinahatami/holdsup/commit/b98453669f82158fb04db5e26a641efebf2d2e96))
* **web:** calmer home page with the claim box as the focal point ([34f0f1d](https://github.com/sinahatami/holdsup/commit/34f0f1d6ac4ab180447eebbd640ada816f399f4d))
* **web:** clear errors with a way to try again, and an offline notice ([7b5250f](https://github.com/sinahatami/holdsup/commit/7b5250f90cd230e210f45d1ac03af5a2bd0f57f8))
* **web:** copy the link or a summary of a check, or share it from the device ([143645d](https://github.com/sinahatami/holdsup/commit/143645dd1cf277ee687b9247e26a12f32ddb0cee))
* **web:** count what HoldsUp can check from the catalog ([2a595bc](https://github.com/sinahatami/holdsup/commit/2a595bca113b81564e342a1d4c5288e62c0d3b38))
* **web:** download the check's notebook from the receipt (P3.6) ([56b13ac](https://github.com/sinahatami/holdsup/commit/56b13aca0c10b4f3fc5dd9f3e7c4c244fb1ba782))
* **web:** draw each finished check at its own link, on the server ([245d283](https://github.com/sinahatami/holdsup/commit/245d28393941bd394fd93daadead002e4b59afd5))
* **web:** english only, and say so ([387920c](https://github.com/sinahatami/holdsup/commit/387920ce2fec02717813a3d534e227c40c7bdc2d))
* **web:** every link off the site opens in a new tab ([a891387](https://github.com/sinahatami/holdsup/commit/a891387ab5c3eb6ca2753b1365ff1802e4fa125d))
* **web:** explain how HoldsUp judges a claim on a methodology page ([c3bdc3f](https://github.com/sinahatami/holdsup/commit/c3bdc3fcfc8b06f352d4fc0aa36c0f1a24a41e85))
* **web:** explain the verdicts on the receipt page, with the tolerance used ([a495f98](https://github.com/sinahatami/holdsup/commit/a495f9871971c4660603be1e2994707d6e54db31))
* **web:** framing checks on each claim (P3.4) ([d0d9e46](https://github.com/sinahatami/holdsup/commit/d0d9e469d9a0fc53161efcd17723e0e3be61db8d))
* **web:** group the indicators page by theme, with counts ([f571b0d](https://github.com/sinahatami/holdsup/commit/f571b0dde14268feb1ff1113f49ff70cf6a7cd85))
* **web:** lay the receipt out in sections, open on the page ([a20033d](https://github.com/sinahatami/holdsup/commit/a20033de145c5ad05336169df000b121239129be))
* **web:** lay the sample receipt out as four equal stages ([a91c789](https://github.com/sinahatami/holdsup/commit/a91c7893530905aca729c93323b30c7e70acb815))
* **web:** let a reader report a wrong match from a claim's receipt ([0c93823](https://github.com/sinahatami/holdsup/commit/0c938233477e134d43c121e59744076b9c3fbfd9))
* **web:** link what HoldsUp can check from the home page and footer ([2b35dee](https://github.com/sinahatami/holdsup/commit/2b35dee044776bf7bfb27df6ef1852145ca62cfb))
* **web:** list recent checks, filtered by verdict, topic and place ([8a82eb8](https://github.com/sinahatami/holdsup/commit/8a82eb8de9979ffdf7a3093813ca2b048186fe01))
* **web:** make the claim box the focal point, quiet the sample receipt ([a2b4ece](https://github.com/sinahatami/holdsup/commit/a2b4ece2799e8cce82b91ff6fbad36feb31a1b05))
* **web:** make the home page lighter, with one pointer per page ([11d975d](https://github.com/sinahatami/holdsup/commit/11d975d1f012c449f16872a512df1217b2bd9af4))
* **web:** make the three "how it works" steps concrete ([5e4727e](https://github.com/sinahatami/holdsup/commit/5e4727e45d6d2ff08189790669bbfda84b2b60bc))
* **web:** mark the current page in the desktop header ([6e169cd](https://github.com/sinahatami/holdsup/commit/6e169cdc1c7cd572ebede3df0e7722db17a03d0b))
* **web:** mark where the trend turns on the time-window heatmap ([4372c73](https://github.com/sinahatami/holdsup/commit/4372c73e6f0139e21b8987d35a9cd7090b9cfd2c))
* **web:** name each claim on multi-claim cards and say how many hold up ([e62a520](https://github.com/sinahatami/holdsup/commit/e62a520648bcfcabafb8fcdefd39858728a7dea5))
* **web:** one short helper line under the claim label ([4792a48](https://github.com/sinahatami/holdsup/commit/4792a48c0dfd104386e7563fdf0dac5cd9eca3da))
* **web:** raise the contrast and size of the home page's secondary text ([48a2cd7](https://github.com/sinahatami/holdsup/commit/48a2cd72e88742cd109253bc9c402129d433d699))
* **web:** reach every page from a menu on a phone ([656a51c](https://github.com/sinahatami/holdsup/commit/656a51c189ba30775df70c3e9101369fe2fc70e5))
* **web:** remember the checks you made, in this browser only ([5d6e595](https://github.com/sinahatami/holdsup/commit/5d6e595fc4018b48fe562c2bea8218baf4b7a95e))
* **web:** restyle the app as an edited denominator (part 1) ([#44](https://github.com/sinahatami/holdsup/issues/44)) ([236017b](https://github.com/sinahatami/holdsup/commit/236017b28f94c833945f3d07018b61c23bb3d4e7))
* **web:** restyle the receipt, chart, heatmap and /eval (redesign part 2) ([#49](https://github.com/sinahatami/holdsup/issues/49)) ([d385cd2](https://github.com/sinahatami/holdsup/commit/d385cd23db28f9ef0d5c65d47fce1c14e91cd6fa))
* **web:** say a verdict is about the number, not the speaker ([6d1f80f](https://github.com/sinahatami/holdsup/commit/6d1f80f93b16f6c694d4316b1653d47d20983f50))
* **web:** say that other time windows are compared now ([2d5f13d](https://github.com/sinahatami/holdsup/commit/2d5f13d7fc4b1293e5bbbf96797f80828e3311e4))
* **web:** say why a claim could not be checked, and what to try ([05feb61](https://github.com/sinahatami/holdsup/commit/05feb6177fd704c0c3e8d657824e9ae23de82bda))
* **web:** search and filter what HoldsUp can check by topic, place and years ([5c151c8](https://github.com/sinahatami/holdsup/commit/5c151c86d74918c6129f1884d889b2f47f6fbc11))
* **web:** show a sample receipt under the claim box ([7682192](https://github.com/sinahatami/holdsup/commit/7682192a26dcc6dacf418db8f802f5cccf96c13f))
* **web:** show the claim, verdict and figures when a check's link is shared ([84110cd](https://github.com/sinahatami/holdsup/commit/84110cd399476d81a15c07f07e1fc5fa5b9df816))
* **web:** show the claimed and the official figure on recent-check cards ([bb9b578](https://github.com/sinahatami/holdsup/commit/bb9b578eafb03948e94b7b3963d94d976d236b66))
* **web:** show the stages of a check as it runs ([355e7d6](https://github.com/sinahatami/holdsup/commit/355e7d607dcddca6e33f7c1e70457f69edc177b4))
* **web:** speak a claim into the box instead of typing it ([474b2e6](https://github.com/sinahatami/holdsup/commit/474b2e6b3d002ed1740a977f167ed7dd5f155ed3))
* **web:** submit with Ctrl or Cmd+Enter, warn near the limit, show a flat disabled button ([ebf28dd](https://github.com/sinahatami/holdsup/commit/ebf28ddee5da0cbd7ab9395f49165f3490270052))
* **web:** tell down from empty on the home page, and help from a 404 ([35caf1d](https://github.com/sinahatami/holdsup/commit/35caf1de11d2aaafe46b58f9196e7e882a589f9c))
* **web:** the cherry-pick heatmap on each claim (P3.2) ([eb1794e](https://github.com/sinahatami/holdsup/commit/eb1794e2ae115a8a3c12016e5eb439d3d3b5f108))
* **web:** the front end, phases 2 to 5 (receipt, supporting pages, history, english only) ([1210ba3](https://github.com/sinahatami/holdsup/commit/1210ba33173506e613c542c04b2cf8527a5cb876))
* **web:** turn the example claims into chips that fill and focus the box ([2e193dd](https://github.com/sinahatami/holdsup/commit/2e193ddbbfe1734ebffeb95de7b2c1c5d8ebb3df))
* **web:** what HoldsUp can check, closest suggestions, one readable model per step ([ab10525](https://github.com/sinahatami/holdsup/commit/ab1052543c420b640618b33a6ef2861c4537a33a))


### Bug Fixes

* **adapters:** handle OWID multi-view and map-first charts ([2501955](https://github.com/sinahatami/holdsup/commit/25019551efc7c9b74dd56303192b54539336d8f2))
* **api:** a rise that comes out flat after inflation is a framing problem ([#47](https://github.com/sinahatami/holdsup/issues/47)) ([682ed51](https://github.com/sinahatami/holdsup/commit/682ed518a46ac7445b882513886413aeb50bde10))
* **api:** flag a trend endpoint that shrinks the change by more than 15% ([#47](https://github.com/sinahatami/holdsup/issues/47)) ([682ed51](https://github.com/sinahatami/holdsup/commit/682ed518a46ac7445b882513886413aeb50bde10))
* **api:** hold a stated value to the digits the claim wrote it with ([#47](https://github.com/sinahatami/holdsup/issues/47)) ([682ed51](https://github.com/sinahatami/holdsup/commit/682ed518a46ac7445b882513886413aeb50bde10))
* **api:** judge a points-or-percent mix-up where its number holds; per-capita series are not totals ([#47](https://github.com/sinahatami/holdsup/issues/47)) ([682ed51](https://github.com/sinahatami/holdsup/commit/682ed518a46ac7445b882513886413aeb50bde10))
* **api:** read a place a plan call names as a country as its code ([#47](https://github.com/sinahatami/holdsup/issues/47)) ([682ed51](https://github.com/sinahatami/holdsup/commit/682ed518a46ac7445b882513886413aeb50bde10))
* **api:** record Gemini's free tier as 20 requests a day ([#45](https://github.com/sinahatami/holdsup/issues/45)) ([c5ec217](https://github.com/sinahatami/holdsup/commit/c5ec2179ab5c63000ba6c8e5c0f1c3e6615f3a98))
* **api:** say on the receipt that a year-only claim date is read as 31 December ([#47](https://github.com/sinahatami/holdsup/issues/47)) ([682ed51](https://github.com/sinahatami/holdsup/commit/682ed518a46ac7445b882513886413aeb50bde10))
* **eval:** a replayed request counts against no provider limit ([#47](https://github.com/sinahatami/holdsup/issues/47)) ([682ed51](https://github.com/sinahatami/holdsup/commit/682ed518a46ac7445b882513886413aeb50bde10))
* **eval:** a run on fallback models is inconclusive, not a regression ([#38](https://github.com/sinahatami/holdsup/issues/38)) ([d3cf000](https://github.com/sinahatami/holdsup/commit/d3cf000c044d66c76110e193233b1277c70aa48a))
* **eval:** ask one model for the whole chatbot baseline ([#54](https://github.com/sinahatami/holdsup/issues/54)) ([a8f7440](https://github.com/sinahatami/holdsup/commit/a8f744084aa1b7d1ba555daab0482a376bf607a6))
* **eval:** retry a rate-limited model call in place, not the whole text ([#34](https://github.com/sinahatami/holdsup/issues/34)) ([ec9b243](https://github.com/sinahatami/holdsup/commit/ec9b2431757516e0ee12b568c8da52cc5bd1261a))
* **eval:** wait out a rate-limited router and retry a text before dropping it ([#33](https://github.com/sinahatami/holdsup/issues/33)) ([e422b0f](https://github.com/sinahatami/holdsup/commit/e422b0fed9ee0b25b636b01f2c1a295702ea6ecd))
* exclude coverage output from eslint ([819bc35](https://github.com/sinahatami/holdsup/commit/819bc35b343cc50abf0abcf2a48ed038031552af))
* **extract:** check "from X to Y" levels as a change ([fc42d50](https://github.com/sinahatami/holdsup/commit/fc42d509cea28591814399d7af662d552fe0585a))
* improve color contrast for WCAG 2 AA compliance ([33fce27](https://github.com/sinahatami/holdsup/commit/33fce2770af1e2952fd12dc59cc24aeb84531418))
* match provider hosts by hostname in list-models ([c3f2525](https://github.com/sinahatami/holdsup/commit/c3f25254dd089d01093e9160d313f3ea52d4627b))
* **ml:** label the unserved confidence model "not served" on /eval ([#56](https://github.com/sinahatami/holdsup/issues/56)) ([5d50b08](https://github.com/sinahatami/holdsup/commit/5d50b088654f0e1ec6f6228e5b86073107dd8279))
* **pipeline:** check dated claims as of their date, read bounds and vague windows ([bfe9704](https://github.com/sinahatami/holdsup/commit/bfe97040c47e9799f35ea7dbc80538ef4f5ada9b))
* **pipeline:** compare yearly values for whole-year claims and keep each level's value ([5c9b98c](https://github.com/sinahatami/holdsup/commit/5c9b98c2198e2f5ead4b7024cb0ea0848190025e))
* **pipeline:** prefer the more frequent series for present claims, add seed --force ([c77aa84](https://github.com/sinahatami/holdsup/commit/c77aa84a236000a65df9f05c0ee2779aa2e938df))
* **pipeline:** read place names as codes, turn two value_at calls into one change ([9dff29b](https://github.com/sinahatami/holdsup/commit/9dff29b6d7c948d203add03200c1908a382c7d4c))
* update provider models and show provider errors in smoke output ([76da526](https://github.com/sinahatami/holdsup/commit/76da526850a5c1cd91da37b45865947aa3342952))
* **web:** cache the gallery read and stream /check/[id] so next build prerenders ([3584af2](https://github.com/sinahatami/holdsup/commit/3584af29f1b7698de17b73133bdd79972a0417fb))
* **web:** keep the footer below the fold while a check loads ([37ebab9](https://github.com/sinahatami/holdsup/commit/37ebab9f5730020a34f50b51ab303d72d360f0f8))
* **web:** make the page background tint visible ([16cd979](https://github.com/sinahatami/holdsup/commit/16cd9798998100457ddb3488e7105b6fa6224256))
* **web:** replace the home example HoldsUp could not check ([#58](https://github.com/sinahatami/holdsup/issues/58)) ([c5cdf5e](https://github.com/sinahatami/holdsup/commit/c5cdf5ea46658a8cd360bbe2511652f0af110f1e))
* **web:** tighten the hero subtitle and make focus rings solid ([31545ae](https://github.com/sinahatami/holdsup/commit/31545aef0ef856bfb273d4abc3051552fa6136c7))


### Performance Improvements

* **api:** find a trend's window by bisection, and build per_year once ([233a410](https://github.com/sinahatami/holdsup/commit/233a410e1cd9cb23a0b50fdff4d0fe9b3925c5bc))
