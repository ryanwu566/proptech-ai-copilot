#!/usr/bin/env python3
"""Read-only loopback acceptance probe. Does not enable providers or call operator routes."""
import json
from pathlib import Path
from urllib.request import Request,build_opener,ProxyHandler,HTTPRedirectHandler
from urllib.parse import urlencode
from urllib.error import HTTPError
from datetime import datetime,timezone
class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None

opener=build_opener(ProxyHandler({}), NoRedirect())
base='http://127.0.0.1:8080'
target={'city':'新北市','district':'新莊區','road':'中正路','building_type':'華廈','area_ping':34,'building_age_years':20,'floor':2}
cases=[('health','GET','/health',None),('readiness','GET','/readiness',None),
 ('demographics_village','GET','/demographics/villages/65000050016/latest',None),
 ('demographics_location','GET','/demographics/location?'+urlencode({'latitude':25.035570879000026,'longitude':121.4525876531026}),None),
 ('valuation_status','GET','/valuation/data-status',None),
 ('valuation_estimate','POST','/valuation/estimate',target),
 ('valuation_trend','POST','/valuation/trend',{k:v for k,v in target.items() if k!='floor'}),
 ('finder','POST','/valuation/property-search',{'city':'新北市','districts':['新莊區'],'budget_max':2000,'limit':5}),
 ('market','POST','/market-insights/query',{'county':'新北市','district':'新莊區','road':'中正路'}),
 ('market_known_special_period','POST','/market-insights/query',{'county':'新北市','district':'新莊區','period':'2026-05'}),
 ('terrain_flood','POST','/terrain-risk/analyze',{'city':'新北市','district':'新莊區','latitude':25.035570879000026,'longitude':121.4525876531026,'include_layers':['flood']})]
fields={'status','data_status','coverage_status','reason_code','active_source','official_records_count','sample_records_count','freshness_status','is_demo_data','is_full_taiwan','transaction_count','average_unit_price','effective_sample_count','analysis_level','fallback_applied','readiness','source_name','source_updated_at'}
results=[]
for name,method,path,payload in cases:
 req=Request(base+path,data=json.dumps(payload).encode() if payload is not None else None,headers={'Content-Type':'application/json','Host':'localhost'},method=method)
 try:
  with opener.open(req,timeout=60) as res: code=res.status; data=json.load(res)
 except HTTPError as exc:
  code=exc.code
  try: data=json.load(exc)
  except Exception: data={}
 except Exception as exc:
  results.append({'name':name,'error_class':type(exc).__name__,'status':'BLOCKED'}); continue
 if not isinstance(data,dict):
  results.append({'name':name,'http_status':code,'status':'BLOCKED','reason_code':'response_not_object'}); continue
 summary={k:v for k,v in data.items() if k in fields and not isinstance(v, (dict, list))}
 record={'name':name,'http_status':code,'summary':summary,'response_keys':sorted(data),'status':'PARTIAL' if code==200 else 'BLOCKED'}
 if name=='health': record['contract_pass']=data.get('status')=='ok' and data.get('readiness')=='ready'
 if name=='readiness': record['contract_pass']=data.get('status')=='ready'
 if name=='demographics_village':
  obs=data.get('observation') if isinstance(data.get('observation'),dict) else {};record['observation']={k:obs.get(k) for k in ['district_code','statistic_yyymm','total_population','household_count']}
  record['contract_pass']=obs.get('district_code')=='65000050016' and obs.get('total_population')==6134 and obs.get('household_count')==3834
 if name=='demographics_location':
  village=data.get('village_resolution') if isinstance(data.get('village_resolution'),dict) else {}
  demographics=data.get('demographics') if isinstance(data.get('demographics'),dict) else {}
  record['contract_pass']=(village.get('district_code')=='65000050016' and demographics.get('total_population')==6134)
  record['location_evidence']={k:data.get(k) for k in ['village_resolution','demographics']}
 if name=='terrain_flood': record['flood']=(data.get('hazards') if isinstance(data.get('hazards'),dict) else {}).get('flood',{})
 if name=='market_known_special_period' and code==200:
  record['known_defect_reproduced']=data.get('transaction_count')==1 and data.get('average_unit_price')==10.15
  record['status']='BLOCKED' if record['known_defect_reproduced'] else 'PARTIAL'
 if name in {'valuation_estimate','valuation_trend','finder'}:
  record['contract_summary']={k:data.get(k) for k in ['valuation_status','estimate_status','trend_status','search_status','source','data_quality','reason_code','message'] if k in data}
 if 'contract_pass' in record:
  record['status']='PASS' if code==200 and record['contract_pass'] else 'BLOCKED'
 results.append(record)
 print(name, code, summary)
Path('reports/professor-final-integration').mkdir(parents=True,exist_ok=True)
Path('reports/professor-final-integration/api-acceptance.json').write_text(json.dumps({'checked_at':datetime.now(timezone.utc).isoformat(),'base_url':base,'checks':results},ensure_ascii=False,indent=2)+'\n')
