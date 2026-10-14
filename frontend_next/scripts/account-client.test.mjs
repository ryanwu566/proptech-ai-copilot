import assert from 'node:assert/strict';
import { test } from 'node:test';
import { readFileSync } from 'node:fs';
import vm from 'node:vm';
import ts from 'typescript';
const user='11111111-1111-4111-8111-111111111111';
const value={user_id:user,status:'active',platform_role:'consumer',created_at:'2026-10-13T00:00:00Z',updated_at:'2026-10-13T00:00:00Z'};
function harness({payload=value,code=200,api='https://api.example.invalid',pending=false}={}) {
  let current=true,expired=0,release;
  const wait=new Promise(resolve=>{release=resolve;});
  const auth={getVNextAccessToken:async()=>({status:'authenticated',accessToken:'fixture-token'}),getVNextSessionGeneration:()=>1,
    isVNextSessionGenerationCurrent:()=>current,expireVNextSession:async()=>{expired++;},
    getVNextAuthClient:()=>({auth:{getSession:async()=>({data:{session:{access_token:'fixture-token',user:{id:user,email:'a@b.invalid',user_metadata:{platform_role:'platform_admin'}}}},error:null})}})};
  const module={exports:{}};
  const source=ts.transpileModule(readFileSync(new URL('../lib/account-client.ts',import.meta.url),'utf8'),{compilerOptions:{module:ts.ModuleKind.CommonJS,target:ts.ScriptTarget.ES2022}}).outputText;
  vm.runInNewContext(source,{module,exports:module.exports,AbortSignal,Date,
    require:name=>name==='@/lib/api'?{API_BASE:api}:auth,
    fetch:async(_url,options)=>{assert.equal(options.redirect,'error');assert.equal(options.credentials,'omit');assert.equal(options.cache,'no-store');if(pending)await wait;return {status:code,ok:code===200,json:async()=>payload};}});
  return {client:module.exports,change:()=>{current=false;release();},expired:()=>expired};
}
test('account display uses authoritative consumer role despite user metadata',async()=>{
  const r=await harness().client.restoreConsumerAccount();assert.equal(r.status,'ready');assert.equal(r.account.platform_role,'consumer');
});
test('suspension remains visible in own account status',async()=>{
  const r=await harness({payload:{...value,status:'suspended'}}).client.restoreConsumerAccount();assert.equal(r.status,'ready');assert.equal(r.account.status,'suspended');
});
test('missing API configuration is unavailable',async()=>assert.equal((await harness({api:''}).client.restoreConsumerAccount()).status,'configuration_unavailable'));
test('mismatched account subject is rejected',async()=>assert.equal((await harness({payload:{...value,user_id:'other'}}).client.restoreConsumerAccount()).status,'account_unavailable'));
test('backend 401 expires only the matching session',async()=>{
  const h=harness({code:401});assert.equal((await h.client.restoreConsumerAccount()).status,'expired_session');assert.equal(h.expired(),1);
});
test('late successful account response after logout is discarded',async()=>{
  const h=harness({pending:true});const result=h.client.restoreConsumerAccount();await Promise.resolve();await Promise.resolve();h.change();assert.equal((await result).status,'missing_session');
});
test('late 401 cannot expire a replacement session',async()=>{
  const h=harness({pending:true,code:401});const result=h.client.restoreConsumerAccount();await Promise.resolve();await Promise.resolve();h.change();assert.equal((await result).status,'missing_session');assert.equal(h.expired(),0);
});
test('unrecognized role and malformed account dates fail closed',async()=>{
  for(const payload of [{...value,platform_role:'owner'},{...value,created_at:'broken'}]) assert.equal((await harness({payload}).client.restoreConsumerAccount()).status,'account_unavailable');
});
