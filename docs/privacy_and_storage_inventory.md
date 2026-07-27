# Privacy and Storage Inventory

This inventory describes the intended client boundary for the release
candidate. It is a contract summary, not a dump of stored values.

## Browser storage

- Saved property cases use the existing `proptech:saved-cases` key only.
- The existing browser storage surfaces are `localStorage` for saved cases and
  `sessionStorage` for short-lived workflow context.
- Workflow navigation and short-lived module context use the existing
  session keys documented in the case workflow code.
- No new release-quality key is added.
- No provider payload, token, credential, or raw error is persisted.

## Sensitive fields

- Saved cases sanitize resolved coordinates and nearest-provider details.
- Market and commute raw rows remain backend-only and are not copied into
  release readiness state.
- Address text is not placed in URL query, hash, cookie, or release reports.
- Secrets remain deployment-managed and are never rendered by the browser.

## Sharing and export

Only the existing allowlisted case summary and browser export surfaces may be
shared. They must use escaped text and omit raw provider payloads, credentials,
coordinates, and private database details. A release readiness result itself is
not a storage key and is not an API response.
