# Property Identity UI slice 1

The reusable `PropertyIdentityReview` component accepts a trusted `PropertyDTO`, the authorized workspace role, and a `PropertyIdentityReviewApi`. The existing `vnextIdentityClient` implements that interface: it reads the current Supabase access token through `vnext-auth-session`, sends the three manual commands with idempotency keys, and validates their proposed/unverified responses. A caller must obtain the property and role from authenticated API reads before mounting the component.

The repository currently has a browser session **reader and refresh path**, but no production sign-in, sign-out, or session creation UI. Therefore this slice does not mount live write controls in the production route. `/vnext/property-identity/preview` supplies fixture data without API traffic in development or the E2E test build; a normal production build returns 404 for it. Its data is visibly marked as demonstration data.

When production authentication UX is available, mount the component inside the authenticated property route using the server-authorized property and role, and pass `vnextIdentityClient` as `api`. Do not derive the role from a token claim or client input. The backend continues to enforce membership and role for every request.

The default graph review requests `confirmed` and `disputed` relations. It requests `proposed` only when the user enables **顯示待確認關係**. Manual parcel, cadastral building number, and parcel↔building commands send only their existing backend request fields. The UI describes all new results as unverified proposals and keeps record IDs in disclosures.
