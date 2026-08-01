# Market data security and privacy

The acquisition client accepts HTTPS URLs only after exact official-domain
allowlist validation, validates redirects, limits bytes/files/extracted size,
rejects ZIP traversal and high compression ratios, and writes downloads through
temporary files before atomic replacement. Failed downloads cannot replace the
last valid release.

CSV parsing is bounded and does not execute formulas. Schema changes, malformed
dates, invalid regions, non-positive prices, duplicate fingerprints, cancelled
records, and unusual notes produce bounded quality events. SQL is parameterized
and public endpoints expose aggregates and privacy-conscious comparable traces,
never raw transaction archives, full addresses, coordinates, or credentials.

The import workflow is protected, single-writer, and least privilege. Database
credentials are runtime secrets. The workflow never prints response bodies,
URLs, headers, SQL, row data, or secret values.
