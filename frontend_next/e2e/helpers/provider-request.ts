import type { Request } from '@playwright/test';

export function isProviderRequest(request: Pick<Request, 'url' | 'method' | 'headers' | 'resourceType'>, baseURL: string) {
  const url = new URL(request.url());
  const sameOrigin = url.origin === new URL(baseURL).origin;
  const routePayload = sameOrigin && request.method() === 'GET' && request.headers().rsc === '1' && url.searchParams.has('_rsc') &&
    (['/', '/cases', '/preferences', '/compare', '/vnext/property-identity'].includes(url.pathname) || /^\/cases\/[^/]+\/(overview|market|location|risk|finance|report|planning|scenarios|decision-room)$/.test(url.pathname));
  return !sameOrigin || (!routePayload && ['fetch', 'xhr'].includes(request.resourceType()));
}
