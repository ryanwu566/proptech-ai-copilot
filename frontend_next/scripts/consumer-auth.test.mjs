import assert from 'node:assert/strict';
import { test } from 'node:test';
import { readFileSync } from 'node:fs';
import vm from 'node:vm';
import ts from 'typescript';
import * as sessionStatus from '../lib/auth-session-status.ts';

const url = 'https://fixture.supabase.co';
const user = '11111111-1111-4111-8111-111111111111';
function token(payload = {}) {
  const part = v => Buffer.from(JSON.stringify(v)).toString('base64url');
  return `${part({alg:'ES256',kid:'fixture'})}.${part({sub:user,iss:`${url}/auth/v1`,aud:'authenticated',role:'authenticated',exp:4102444800,...payload})}.signature`;
}
function harness(result, env = {}, transport = fetch, abortSignal = AbortSignal) {
  let calls = 0;
  const listeners = [];
  const sdk = { auth: {
    onAuthStateChange: callback => { listeners.push(callback); return {data:{subscription:{unsubscribe(){}}}}; },
    signUp: async () => { calls++; if (result.data?.session) listeners.forEach(f => f('SIGNED_IN')); return result; },
    resetPasswordForEmail: async () => { calls++; return result; },
    signOut: async () => ({error:result.logoutError??null}),
  }};
  const module = {exports:{}};
  const source = ts.transpileModule(readFileSync(new URL('../lib/vnext-auth-session.ts',import.meta.url),'utf8'),{compilerOptions:{module:ts.ModuleKind.CommonJS,target:ts.ScriptTarget.ES2022}}).outputText;
  let clientOptions;
  vm.runInNewContext(source,{module,exports:module.exports,require:name=>name==='./auth-session-status'?sessionStatus:({createClient:(_url,_key,options)=>{clientOptions=options;return sdk;}}),
    process:{env:{NODE_ENV:'production',NEXT_PUBLIC_SUPABASE_URL:url,NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY:'sb_publishable_fixture_public',...env}},window:{dispatchEvent(){}},atob,URL,Event,fetch:transport,AbortSignal:abortSignal});
  return {auth:module.exports,calls:()=>calls,options:()=>clientOptions};
}

test('signup with a valid provider session authenticates through the existing client',async()=>{
  const h=harness({data:{session:{access_token:token()},user:{id:user}},error:null});
  assert.equal((await h.auth.signUpVNext('person@example.invalid','valid-password')).status,'authenticated');
});
test('signup without session preserves confirmation uncertainty',async()=>{
  const h=harness({data:{session:null,user:{id:user}},error:null});
  assert.equal((await h.auth.signUpVNext('person@example.invalid','valid-password')).status,'confirmation_required');
});
test('duplicate email errors are normalized to accepted without disclosing registration',async()=>{
  const h=harness({data:{session:null,user:null},error:{code:'user_already_exists',message:'sensitive provider message'}});
  const r=await h.auth.signUpVNext('person@example.invalid','valid-password');
  assert.equal(r.status,'request_accepted'); assert.equal(JSON.stringify(r).includes('sensitive'),false);
});
for (const [email,password] of [['','valid-password'],['broken','valid-password'],['a@b.invalid','short'],['a@b.invalid','x'.repeat(1025)]]) {
  test(`invalid signup input is rejected before SDK use (${email || 'empty'})`,async()=>{
    const h=harness({}); assert.equal((await h.auth.signUpVNext(email,password)).status,'validation_error'); assert.equal(h.calls(),0);
  });
}
test('absent public auth config is unavailable',async()=>{
  const h=harness({}, {NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY:''});
  assert.equal((await h.auth.signUpVNext('a@b.invalid','valid-password')).status,'configuration_unavailable');
});
test('provider failures expose only a bounded state',async()=>{
  const h=harness({data:{session:null,user:null},error:{message:'password token database secret'}});
  assert.equal(JSON.stringify(await h.auth.signUpVNext('a@b.invalid','valid-password')),'{"status":"provider_error"}');
});
test('invalid privileged signup session fails closed',async()=>{
  const h=harness({data:{session:{access_token:token({role:'service_role'})}},error:null});
  assert.equal((await h.auth.signUpVNext('a@b.invalid','valid-password')).status,'provider_error');
});
test('reset request reports acceptance rather than delivery',async()=>{
  const h=harness({data:{},error:null}); assert.equal((await h.auth.requestPasswordResetVNext('a@b.invalid')).status,'request_accepted');
});
test('shared SDK transport has an abortable deadline and preserves caller cancellation',async()=>{
  const controller=new AbortController(); controller.abort();
  const h=harness({}, {}, async (_url,init)=>{assert.equal(init.signal.aborted,true);throw new Error('aborted');},
    {timeout:ms=>{assert.equal(ms,10000);return controller.signal;},any:AbortSignal.any});
  h.auth.getVNextAuthClient();
  assert.equal(typeof h.options().global?.fetch,'function');
  await assert.rejects(h.options().global.fetch(`${url}/auth/v1/signup`,{signal:controller.signal}),/aborted/);
});
test('logout provider errors do not report successful signout',async()=>{
  const h=harness({logoutError:{message:'private provider error'}});
  assert.equal(await h.auth.signOutVNext(),false);
});
