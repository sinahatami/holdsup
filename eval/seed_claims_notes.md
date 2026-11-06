# Seed claims: notes for P1.12 and P4.1

Each claim in `seed_claims.csv` was checked by a professional fact-checker (Pagella Politica, Full Fact, PolitiFact, Africa Check, Ballotpedia, Media Bias/Fact Check) or reported in a fact-check roundup. Italian claims are translated and shortened. The fact-checker's verdict is a starting point for your own label, not a replacement: HoldsUp checks against official series, which can differ from the national statistics office a fact-checker used.

"Likely source" codes are suggestions to verify when writing the catalog.

| id | Fact-checker verdict (paraphrased) | Likely source | What it tests |
| --- | --- | --- | --- |
| c001 | True; 44% start point slightly high (43.4%) | Eurostat `une_rt_m` (under 25) | Rounding tolerance |
| c002 | Trend right; value slightly low (actual 38.4%) | Eurostat `une_rt_m` (under 25) | Value just outside tolerance |
| c003 | True | Eurostat `une_rt_m` | "Since 1977" is ISTAT's series; Eurostat monthly data starts later (coverage mismatch) |
| c004 | Not in summary; check yourself | Eurostat `une_rt_m` | Two-point comparison across years |
| c005 | Misleading: comparing absolute records across eras | Eurostat `lfsi_emp_a` | "Since Garibaldi" predates any series (framing, partly can't check) |
| c006 | Correct (133.3% in Q2 2013) | Eurostat `gov_10q_ggdebt` | Quarterly vs annual series |
| c007 | First part true | Eurostat `gov_10dd_edpt1` | Multi-part claim |
| c008 | True in absolute euros; debt-to-GDP had fallen | Eurostat `gov_10dd_edpt1` (both units) | Absolute vs ratio distortion |
| c009 | Not verifiable | Bank of Italy monthly (not in sources) | Should end as "can't check" |
| c010 | Correct (2023 vs 2020: Italy +14.8%, France +10.6%, Germany +4.8%) | Eurostat `nama_10_gdp` (volumes) | Base year is the 2020 crash: change-point flag |
| c011 | Partly right | Eurostat `namq_10_gdp` | Quarterly, year-on-year vs quarter-on-quarter |
| c012 | Forecast at the time; now checkable with 2024 actuals | Eurostat `nama_10_gdp` | Forecast claims; partly supported |
| c013 | False: confuses growth rate with GDP level | Eurostat regional GDP | Rate vs level; future claim |
| c014 | Correct per ISTAT | Eurostat `demo_find` / World Bank `SP.DYN.TFRT.IN` | Data lag: latest year may be missing |
| c015 | Correct per ISTAT | Eurostat `demo_gind` | "Since unification" (1861) predates the data |
| c016 | Correct | Eurostat `demo_gind` (crude birth rate) | Ranking across countries |
| c017 | True | Eurostat `nrg_ind_ren` | Comparing against a target (17%) |
| c018 | Reported in a fact-check roundup; no verdict | Eurostat `env_air_gge` or OWID | 1990 base year |
| c019 | Incorrect: about 19% of final consumption, about 21% of primary energy | Eurostat `nrg_ind_ren` / OWID | Definition differences |
| c020 | Inaccurate: rose overall, not every month | UK monthly data (not in sources) | Should end as "can't check" |
| c021 | Incorrect: average about 6%, peak 8.3% | World Bank `SL.UEM.TOTL.ZS` (UK) | Clearly not supported |
| c022 | Incorrect: stalling, not falling | World Bank `SP.DYN.LE00.IN` / OWID | Trend framing |
| c023 | Justifiable but not clear-cut (UK about level with Germany in 2016) | World Bank `NY.GDP.MKTP.KD.ZG` (G7) | Ranking with a near-tie |
| c024 | Correct for per capita; total emissions fell less | OWID CO₂ per capita | Per capita vs absolute |
| c025 | False (closer to 30%) | OWID share of global CO₂ | Clearly not supported |
| c026 | Half true | OWID annual CO₂ by country | Absolute vs percentage reduction |
| c027 | False | OWID annual CO₂ by country | Ranking by rate of change |
| c028 | Mostly correct (national "narrow" definition) | World Bank `SL.UEM.TOTL.ZS` | Definition mismatch: ILO model vs national statistics |
| c029 | Incorrect (about 20% to 24.7%) | World Bank `SL.UEM.TOTL.ZS` | Percent vs percentage points |
| c030 | False (3.5% in June 2026 vs 3.0% in January 2025) | US monthly CPI (not in sources) | Should end as "can't check" (stale annual data) |

Rough mix: about 11 supported, 7 not supported, 8 framing problems, 4 can't check.
