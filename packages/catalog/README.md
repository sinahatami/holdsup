# Indicator catalog

One YAML file per indicator in `indicators/`, named `<id>.yaml`. The catalog has its own version in `VERSION` (SemVer), stamped on every receipt; bump it whenever entries change.

```bash
make catalog-check   # validate only (no database, no model)
make catalog         # validate, embed (fastembed, local), and sync the `indicators` table
```

`make catalog` mirrors this folder: entries removed here are deleted from the table.

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

`filters` (not in the original spec list) holds the fixed query dimensions an adapter needs to get exactly this series: Eurostat dimension codes; for OWID, `column` when a chart has several value columns; empty for most World Bank indicators.

Rules the validator enforces: unknown fields are rejected; 3–5 unique aliases that don't repeat the name; `definition` 10–500 characters; `last_year ≥ first_year`; every `related` id exists and is not the entry itself; no two entries point at the same source series with the same filters.

What gets embedded for search: `"{name}. Also called: {aliases}. {definition}"`.
