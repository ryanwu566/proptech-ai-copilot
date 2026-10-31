import { test } from 'node:test';
import assert from 'node:assert/strict';
import { inspectAsset } from '../scripts/ops/professor_stage4a_public_authority.mjs';

const origin='https://flyhsjcynreuofbcdxod.supabase.co';
const reviewedPath='/_next/static/immutable/chunks/28_mshq0x50li.js';
const options='{auth:{persistSession:!0,autoRefreshToken:!0,detectSessionInUrl:!1}}';
const config=`function cfg(){let key=PUBLIC_KEY;if(!/^sb_publishable_/.test(key))return null;let parsed=new URL('${origin}');return{url:parsed.origin,key:key};}`;

for(const [name,code] of [
 ['well-shaped but unreviewed source',config+`function client(){let c=cfg();return new SDK(c.url,c.key,${options});}`],
 ['shadowed configuration function',config+`function client(){let cfg=()=>OTHER;let c=cfg();return SDK(c.url,c.key,${options});}`],
 ['shadowed receiver',config+`function client(){let c=cfg();{let c=OTHER;return SDK(c.url,c.key,${options});}}`],
 ['mutated config URL',config+`function client(){let c=cfg();c.url=OTHER;return SDK(c.url,c.key,${options});}`],
 ['mutated parsed URL',`function cfg(){let key=PUBLIC_KEY;let parsed=new URL('${origin}');parsed.hostname=OTHER;return{url:parsed.origin,key:key};}`],
 ['unused helper and unrelated SDK-like marker',config+`function unused(){let c=cfg();return anything(c.url,c.key,${options});}`],
 ['misleading second URL argument',`function cfg(){let key=PUBLIC_KEY;let parsed=new URL(OTHER,'${origin}');return{url:parsed.origin,key:key};}`],
 ['malformed JavaScript','function incomplete('],
]){
 test(name+' cannot establish authority without reviewed byte identity',()=>{
  const result=inspectAsset(Buffer.from(code),reviewedPath);
  assert.equal(result.configuration_bindings.length,0);
  assert.equal(result.binding_proof,'not_reviewed');
  assert.equal(JSON.stringify(result).includes('PUBLIC_KEY'),false);
 });
}
