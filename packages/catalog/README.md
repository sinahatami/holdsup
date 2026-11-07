# Indicator catalog

One YAML file per indicator in `indicators/`, named `<id>.yaml`. The catalog has its own version in `VERSION` (SemVer), stamped on every receipt; bump it whenever entries change.

```bash
make catalog-check   # validate only (no database, no model)
make catalog         # validate, embed (fastembed, local), and sync the `indicators` table
```

`make catalog` mirrors `indicators/`: entries removed there are deleted from the table.

`drafts/` holds unfinished entries (for example with `aliases: []`). The validator and loader only read `indicators/*.yaml`, so drafts are never checked or loaded. To publish a draft: fill in the `# TODO (you)` fields, move it to `indicators/`, bump `VERSION`, and run `make catalog-check`.

## Entry format

```yaml
id: youth_unemployment_rate          # lowercase snake_case; must equal the file name
source: eurostat                     # eurostat | worldbank | owid | datacommons
source_code: une_rt_a                # dataset code, indicator code, or OWID chart slug
name: Youth unemployment rate
aliases:                             # 3–5 phrases people actually say; not the name again
  - youth unemployment
  - jobless rate for young people
  - unemployment among under-25s
definition: Unemployed people aged 15 to 24 as a percentage of the labour force of the same age, annual average.
unit: "% of labour force aged 15-24"
frequency: annual                    # annual | quarterly | monthly
geo_coverage: [EU27_2020, IT, DE]    # codes as the source writes them
first_year: 2009
last_year: null                      # null = still updated
related: [unemployment_rate]         # ids of other entries (per-capita, real vs nominal, denominator)
filters: { sex: T, age: Y15-24, unit: PC_ACT }   # fixed adapter filters, not geo or time
```

Monthly and quarterly entries also set `annual_value`, how code makes a year's value when a claim names a whole year ("in 2015"): `mean` (the average of the year's months or quarters: rates, shares, year-on-year growth) or `end` (the last month or quarter: stocks such as debt to GDP). Leave it out when no yearly value can be made from the series (growth on the previous quarter); such a series then only answers claims about one month or quarter, or a trend. Only complete years are used, and the receipt says how each yearly value was made.

`filters` (not in the original spec list) holds the fixed query dimensions an adapter needs to get exactly this series: Eurostat dimension codes; for OWID, `column` when a chart has several value columns; empty for most World Bank indicators.

Rules the validator enforces: unknown fields are rejected; 3–5 unique aliases that don't repeat the name; `definition` 10–500 characters; `last_year ≥ first_year`; every `related` id exists and is not the entry itself; no two entries point at the same source series with the same filters.

What gets embedded for search: `"{name}. Also called: {aliases}. {definition}"`.
