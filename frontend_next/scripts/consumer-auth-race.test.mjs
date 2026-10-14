import assert from "node:assert/strict";
import { test } from "node:test";
import { readFileSync } from "node:fs";
import vm from "node:vm";
import ts from "typescript";
import { createClient } from "@supabase/supabase-js";

const user = "11111111-1111-4111-8111-111111111111";
const url = "https://fixture.supabase.co";
const part = value => Buffer.from(JSON.stringify(value)).toString("base64url");
const token = `${part({alg:"ES256",kid:"fixture"})}.${part({sub:user,iss:`${url}/auth/v1`,aud:"authenticated",role:"authenticated",exp:4102444800})}.signature`;
const session = {access_token:token,refresh_token:"fixture-refresh",token_type:"bearer",expires_in:3600,expires_at:4102444800,user:{id:user,email:"person@example.invalid",aud:"authenticated",created_at:"2026-10-14T00:00:00Z"}};
function deferred() { let resolve; const promise = new Promise(done => { resolve = done; }); return {promise,resolve}; }

for (const action of ["signup", "login"]) for (const external of [false, true]) {
  test(`real SDK delayed ${action} cannot restore a session after ${external ? "SDK signout notification" : "local logout"}; later deliberate login works`, async () => {
    const started = deferred(), response = deferred();
    const persisted = new Map();
    let delayed = true;
    const transport = async input => {
      const path = new URL(input).pathname;
      if (path.endsWith("/signup") || path.endsWith("/token")) {
        if (delayed) { started.resolve(); await response.promise; }
        return new Response(JSON.stringify(session), {status:200,headers:{"Content-Type":"application/json"}});
      }
      return new Response("{}", {status:200,headers:{"Content-Type":"application/json"}});
    };
    const module = {exports:{}};
    const source = ts.transpileModule(readFileSync(new URL("../lib/vnext-auth-session.ts",import.meta.url),"utf8"), {compilerOptions:{module:ts.ModuleKind.CommonJS,target:ts.ScriptTarget.ES2022}}).outputText;
    vm.runInNewContext(source, {module,exports:module.exports,require:()=>({createClient:(endpoint,key,options)=>createClient(endpoint,key,{...options,auth:{...options.auth,autoRefreshToken:false,storage:{getItem:key=>persisted.get(key)??null,setItem:(key,value)=>persisted.set(key,value),removeItem:key=>persisted.delete(key)}}})}),
      process:{env:{NODE_ENV:"production",NEXT_PUBLIC_SUPABASE_URL:url,NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY:"sb_publishable_fixture_public"}},window:{dispatchEvent(){}},atob,URL,Event,AbortSignal,fetch:transport});
    const auth = module.exports;
    await auth.getVNextAuthClient().auth.getSession();
    const pending = action === "signup" ? auth.signUpVNext("person@example.invalid","valid-password") : auth.signInVNext("person@example.invalid","valid-password");
    await started.promise;
    const logout = external ? auth.getVNextAuthClient().auth.signOut({scope:"local"}).then(result=>!result.error) : auth.signOutVNext();
    assert.equal((await auth.getVNextAccessToken()).status,"missing_session");
    response.resolve();
    const outcome = await pending;
    assert.equal(action === "signup" ? outcome.status : outcome, action === "signup" ? "provider_error" : false);
    assert.equal(await logout,true);
    assert.equal((await auth.getVNextAccessToken()).status,"missing_session");
    await auth.signOutVNext();
    assert.equal((await auth.getVNextAuthClient().auth.getSession()).data.session,null);
    assert.equal([...persisted.keys()].some(key=>key.endsWith("auth-token")),false);
    delayed = false;
    assert.equal(await auth.signInVNext("person@example.invalid","valid-password"),true);
    assert.equal((await auth.getVNextAccessToken()).status,"authenticated");
    await auth.signOutVNext();
  });
}
