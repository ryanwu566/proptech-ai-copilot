# Market Insight methodology v1

The default population is residential existing-property sale transactions.
Presale and rental records are not combined with sale statistics. The primary
headline is the median unit price per square metre; arithmetic mean and
quartiles are descriptive context. A result carries its period, category,
sample size, source release, source update date, coverage status, and
aggregation version.

Sample status is `sufficient` at ten or more valid records, `limited` at three
to nine, `insufficient` at one or two, and `no_data` at zero. Trend changes are
not shown when either comparison period lacks sufficient evidence. Missing data
is not rendered as zero or as a low-price conclusion.

Comparables are bounded deterministic references. They use canonical county,
district, category, building type, area similarity, and date recency where
available. Public results omit full addresses and internal identifiers. The
engine is not an appraisal and does not guarantee market value.

## Road-level analysis

A request with a road uses only existing official PLVR historical transaction
rows. It does not use listing inventory, a listing provider, scraping, building
or community matching, geocoding, or coordinates. The requested location and
the scope actually used for statistics are returned and displayed separately.

Road identity is exact after a deliberately narrow normalization step:

- trim and remove whitespace;
- treat `臺` and `台` as the same spelling;
- normalize Arabic section numbers 1 through 10 before `段` to Chinese
  numerals; and
- require a bounded road, street, or boulevard name, optionally followed by a
  section.

There is no fuzzy road match, neighboring-road match, building-type fallback,
city fallback, or time-window widening. Full addresses and address-like input
are rejected.

The analysis window is the current transaction month plus the preceding 35
months. Sample counts are calculated only after filtering for the official
PLVR source, exact canonical county/district, a valid in-window period, a valid
road identity, and valid price, total-price, and area values. Future periods
and older periods are excluded before the threshold is evaluated.

Scope selection is deterministic:

1. `ROAD` when the exact normalized road has at least 10 valid rows;
2. `DISTRICT` when the road has fewer than 10 rows but its district has at
   least 10 valid rows; or
3. `NOT_AVAILABLE` when the district also has fewer than 10 valid rows.

Only one effective scope supplies the headline metrics and chart series. A
district fallback never mixes road-only observations into separate headline
statistics or labels district statistics as road statistics. `NOT_AVAILABLE`
returns no headline metrics and empty chart series, while retaining safe sample
counts and an explanation.

Supported road-analysis summaries are median and quartile unit price in ten
thousand NTD per ping, median total price in ten thousand NTD, median area in
ping, and monthly/yearly effective-scope series. Year-over-year change is shown
only when both compared yearly buckets contain at least 10 effective-scope
rows. Volatility is shown only when at least three monthly medians exist.

All road-level results remain historical market background. They do not imply
that a property is currently listed, available, or offered for sale.
