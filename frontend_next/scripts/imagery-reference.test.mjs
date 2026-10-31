import assert from 'node:assert/strict';
import {test} from 'node:test';
import {readFileSync} from 'node:fs';
import vm from 'node:vm';
import ts from 'typescript';
function compile(path, require = () => ({})) {
 const module = {exports:{}};
 vm.runInNewContext(ts.transpileModule(readFileSync(new URL(path,import.meta.url),'utf8'),{compilerOptions:{module:ts.ModuleKind.CommonJS,target:ts.ScriptTarget.ES2022,jsx:ts.JsxEmit.ReactJSX}}).outputText,{module,exports:module.exports,require,AbortController});
 return module.exports;
}
const helper = compile('../lib/imagery-reference.ts');
const {imageryMetadata, embeddedJpeg} = helper;
test('NLSC unknown vintage is aerial context, never a capture date',()=>{
 const m=imageryMetadata({provider:'nlsc_photo2',retrieval_time:'2026-10-30',cloud_filter_percent:35});
 assert.equal(m.titleKey,'commercial.orthophotoTitle'); assert.equal(m.showCloud,false); assert.equal(m.captureDate,null);
});
test('annual SPOT mosaic keeps annual vintage distinct from exact observation',()=>{
 const m=imageryMetadata({provider:'csrsr_spot',vintage:'2024',date_precision:'year',retrieval_time:'2026-10-30'});
 assert.equal(m.annual,true); assert.equal(m.captureDate,null); assert.equal(m.vintage,'2024');
});
test('only explicit EE or explicit legacy dataset enables applicable clouds',()=>{
 assert.equal(imageryMetadata({dataset:'COPERNICUS/S2_SR_HARMONIZED',cloud_filter_percent:35}).showCloud,true);
 assert.equal(imageryMetadata({provider:'unknown',cloud_filter_percent:35}).showCloud,false);
 assert.equal(imageryMetadata({provider:'earth_engine',cloud_filter_percent:null}).showCloud,false);
});
test('only embedded JPEG is displayable; remote URLs never trigger image fetch',()=>{
 assert.equal(embeddedJpeg('https://example.com/a.jpg'),null);
 assert.equal(embeddedJpeg('data:image/png;base64,YQ=='),null);
 assert.equal(embeddedJpeg('data:image/jpeg;base64,/9j/YQ=='),'data:image/jpeg;base64,/9j/YQ==');
});

test('render, effects, and coordinate updates do not request imagery; explicit button does',async()=>{
 let calls=0, cursor=0; const slots=[], effects=[];
 const hooks={useRef(value){const i=cursor++; return slots[i]??(slots[i]={current:value});},useState(value){const i=cursor++; if(!(i in slots))slots[i]=value; return [slots[i],v=>{slots[i]=v;}];},useEffect(effect){effects.push(effect);}};
 const jsx=(type,props)=>({type,props});
 const {SatelliteEvidence}=compile('../components/satellite-evidence.tsx', name=>name==='react'?hooks:name==='react/jsx-runtime'?{jsx,jsxs:jsx,Fragment:'fragment'}:name.includes('imagery-reference')?helper:name.includes('experience-locale')?{useExperienceLocale:()=>({t:k=>k,locale:'en'})}:name.includes('/api')?{api:{satelliteReference:async()=>{calls++;return {};}}}:{default:'image'});
 const render=coordinate=>{cursor=0;return SatelliteEvidence({coordinate});};
 const coordinate={accepted:true,latitude:25,longitude:121};
 let tree=render(coordinate); effects.splice(0).forEach(f=>f()); assert.equal(calls,0);
 tree=render({...coordinate,longitude:122}); effects.splice(0).forEach(f=>f()); assert.equal(calls,0);
 function find(node){if(!node || typeof node !== 'object')return; if(node?.props?.['data-testid']==='satellite-request-action')return node;for(const child of [node?.props?.children].flat(Infinity)){const match=find(child);if(match)return match;}}
 find(tree).props.onClick(); await Promise.resolve(); assert.equal(calls,1);
});
test('neutral initial wording and provider-specific titles are translated',()=>{
 const {translateExperience:t}=compile('../lib/experience-i18n.ts',()=>({getExperienceOverride:()=>undefined}));
 assert.equal(t('zh-TW','commercial.satelliteTitle'),'地表影像參考');
 assert.equal(t('zh-TW','commercial.orthophotoTitle'),'航空正射影像參考');
 assert.equal(t('zh-TW','commercial.actualSatelliteTitle'),'衛星影像參考');
 assert.match(t('en','commercial.annualMosaic'),/not single-date/);
 assert.match(t('en','commercial.noncommercial'),/Noncommercial/);
 assert.doesNotMatch(t('en','commercial.satelliteLoading'),/satellite|Sentinel|composite/);
});
test('parent risk disclosure uses provider-neutral imagery labels in every locale',()=>{
 const {riskBuyerCopy}=compile('../lib/workspace/risk-buyer-copy.ts');
 assert.equal(riskBuyerCopy('zh-TW').satellite,'地表影像參考（輔助證據）');
 assert.equal(riskBuyerCopy('en').satellite,'Imagery reference (supporting evidence)');
 assert.equal(riskBuyerCopy('ja').satellite,'地表画像の参考（補助証拠）');
 assert.equal(riskBuyerCopy('ko').satellite,'지표 영상 참고 (보조 근거)');
});
