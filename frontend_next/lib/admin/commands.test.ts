import assert from 'node:assert/strict';
import test from 'node:test';
// @ts-expect-error Native TS runner extension.
import { adminRequest } from './transport.ts';

test('command retries preserve body and key and never follow redirects', async () => {
  const calls: RequestInit[] = [];
  const deps = { base: 'https://api.invalid', fetcher: async (_: unknown, init?: RequestInit) => { calls.push(init!); return Response.json({ command_id: 'fixture' }); },
    session: async () => ({ status: 'authenticated' as const, accessToken: 'verified' }), generation: () => 1, current: () => true, expire: async () => {} };
  const body = { command_id: 'same-key', reason: 'investigation' };
  for (let i=0;i<2;i++) await adminRequest(deps, '/quota-policy/commands', body);
  assert.equal(calls[0].body, calls[1].body);
  assert.equal(calls[0].method, 'POST');
  assert.equal(calls[0].redirect, 'error');
  await assert.rejects(adminRequest(deps, '/../../provider', body));
});

test('revocation during a mutation prevents late result rendering', async () => {
  let current = true;
  const deps = { base: 'https://api.invalid', fetcher: async () => { current=false; return Response.json({ private: true }); },
    session: async () => ({ status: 'authenticated' as const, accessToken: 'verified' }), generation: () => 1, current: () => current, expire: async () => {} };
  await assert.rejects(adminRequest(deps, '/quota-policy/commands', { command_id: 'same-key' }), { message: 'authentication' });
});

test('deterministic command validation and not-found errors are distinct from uncertain failures', async () => {
  const deps = { base: 'https://api.invalid', fetcher: async () => Response.json({}, { status: 422 }),
    session: async () => ({ status: 'authenticated' as const, accessToken: 'verified' }), generation: () => 1, current: () => true, expire: async () => {} };
  await assert.rejects(adminRequest(deps, '/quota-policy/commands', { command_id: 'fixture' }), { message: 'invalid_command' });
  deps.fetcher = async () => Response.json({}, { status: 404 });
  await assert.rejects(adminRequest(deps, '/quota-policy/commands', { command_id: 'fixture' }), { message: 'not_found' });
});
