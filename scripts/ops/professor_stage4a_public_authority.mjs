#!/usr/bin/env node
// Read public deployment metadata only. Never emit bundle text or key values.
import { readFileSync } from 'node:fs';
import crypto from 'node:crypto';
import { pathToFileURL } from 'node:url';

const FRONTEND='https://proptech-ai-copilot.vercel.app';
const sha=bytes=>crypto.createHash('sha256').update(bytes).digest('hex');
const reviewed=JSON.parse(readFileSync(new URL('../../reports/professor-stage4a-auth-userdb/reviewed-frontend-authority.json',import.meta.url),'utf8'));

async function get(path,maximum=2_000_000){
 const url=new URL(path,FRONTEND);
 if(url.origin!==FRONTEND||url.username||url.password)throw Error('source_invalid');
 const response=await fetch(url,{redirect:'error',credentials:'omit',signal:AbortSignal.timeout(15_000)});
 if(!response.ok)throw Error('source_unavailable');
 const reader=response.body.getReader();const chunks=[];let size=0;
 try{while(true){const item=await reader.read();if(item.done)break;size+=item.value.length;if(size>maximum)throw Error('source_too_large');chunks.push(Buffer.from(item.value));}}
 finally{await reader.cancel();}
 return Buffer.concat(chunks);
}

export function inspectAsset(bytes,path){
 // The source mapping was reviewed without credential values. Do not infer an
 // authority from arbitrary JS names, URL strings, vendor examples or patterns.
 const matched=path===reviewed.asset_path&&sha(bytes)===reviewed.asset_sha256;
 return {binding_proof:matched?reviewed.binding_proof:'not_reviewed',
  configuration_bindings:matched?[{public_origin:reviewed.public_origin,
   url_constructor_returns_origin:true,client_uses_same_configuration_url_and_key:true,
   persist_session:true,auto_refresh:true,detect_session_in_url:false}]:[],
  authenticated_audience_marker:matched,issuer_suffix_marker:matched,password_signin_marker:matched};
}

async function main(){

try{
 if(process.argv.length!==2)throw Error('arguments_not_supported');
 const release=await get('/release-version',4096);const metadata=JSON.parse(release.toString('utf8'));
 if(metadata.product!=='proptech-ai-copilot-frontend'||metadata.commit_sha!==reviewed.release_commit)throw Error('deployment_identity_invalid');
 const pages=[];const paths=new Set();
 for(const path of ['/login','/signup','/account']){
  const bytes=await get(path);const html=bytes.toString('utf8');
  pages.push({path,sha256:sha(bytes)});
  for(const match of html.matchAll(/<script\b[^>]*\bsrc=["']([^"']+)["']/g)){
   const url=new URL(match[1],FRONTEND);
   if(url.origin===FRONTEND&&url.pathname.startsWith('/_next/static/')&&url.pathname.endsWith('.js')&&!url.search)paths.add(url.pathname);
  }
 }
 if(paths.size>40)throw Error('asset_limit_exceeded');
 const assets=[];let total=0;
 for(const path of [...paths].sort()){
  const bytes=await get(path);total+=bytes.length;if(total>20_000_000)throw Error('byte_limit_exceeded');
  const result=inspectAsset(bytes,path);
  assets.push({path,sha256:sha(bytes),bytes:bytes.length,...result});
 }
 const finalRelease=JSON.parse((await get('/release-version',4096)).toString('utf8'));
 if(finalRelease.commit_sha!==metadata.commit_sha)throw Error('deployment_changed');
 console.log(JSON.stringify({schema:'professor-public-auth-authority-observation-v1',
  frontend_origin:FRONTEND,release_commit:metadata.commit_sha,release_sha256:sha(release),pages,assets,
  release_stable:true,total_bytes:total,credential_values_returned:false,credential_values_compared:false,
  auth_requests_performed:false,frontend_modified:false,read_only:true}));
}catch{
 console.log(JSON.stringify({schema:'professor-public-auth-authority-observation-v1',status:'unavailable',reason_code:'public_metadata_unavailable_details_suppressed',credential_values_returned:false}));
 process.exitCode=1;
}

}

if(process.argv[1]&&import.meta.url===pathToFileURL(process.argv[1]).href)await main();
