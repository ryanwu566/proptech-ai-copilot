"""Offline, bounded historical staging. No serving DB, credentials or network.

Raw files are opened read-only. All writes belong to a new private output tree.
Quarter labels do not establish publication time or authoritative revision order.
"""
from __future__ import annotations

from collections import Counter
from datetime import date
from decimal import Decimal, InvalidOperation
import csv
import gzip
import hashlib
import io
import json
import math
import os
from pathlib import Path, PurePosixPath
import re
import resource
import time
import shutil
import sqlite3
import stat
import unicodedata
import uuid
import zipfile

from services.plvr_import_service import FILE_CITY_MAP, normalize_row
from scripts.ml.semantics import parse_roc_date, parse_floor, parse_counts, age_at_transaction

VERSION='plvr-local-canonical-history-v1'
KNOWN_SERIAL='RPWNMLNKNHLGFBF78EA'
MAX_MEMBER=128*1024**2
MAX_MEMBERS=1000
RELEASE_RE=re.compile(r'([0-9]{3})S([1-4])')
MAIN_RE=re.compile(r'([a-z])_lvr_land_a\.csv')
REQUIRED=('鄉鎮市區','交易標的','土地位置建物門牌','交易年月日','建物型態',
          '建物移轉總面積平方公尺','總價元','備註','編號')
FORBIDDEN_OUTPUT=(Path('/srv/proptech-data'),Path('/run/media/andy/Crucial X9'),
                  Path('/home/andy/proptech-ai-copilot'))


def canonical(value):
    return json.dumps(value,ensure_ascii=False,sort_keys=True,separators=(',',':'),allow_nan=False).encode()


def sha(value):return hashlib.sha256(value).hexdigest()


def text(value):
    return unicodedata.normalize('NFKC',str(value or '')).strip().replace('臺','台')


def open_source(path):
    # O_NOATIME avoids source file metadata updates on supported Linux filesystems.
    flags=os.O_RDONLY|os.O_NOFOLLOW|getattr(os,'O_NOATIME',0)
    fd=os.open(path,flags)
    if not stat.S_ISREG(os.fstat(fd).st_mode):
        os.close(fd);raise ValueError('source_not_regular')
    return os.fdopen(fd,'rb')


def hash_file(path):
    with open_source(path) as f:return hashlib.file_digest(f,'sha256').hexdigest()


def _decimal(value):
    try:
        raw=text(value).replace(',','')
        if not re.fullmatch(r'[+-]?[0-9]+(?:\.[0-9]+)?',raw) or len(raw)>80:return None
        result=Decimal(raw)
        return result if result.is_finite() else None
    except InvalidOperation:return None


def _number_string(value):
    return format(value.normalize(),'f') if value is not None else None


def row_evidence(raw, county, as_of):
    serial=text(raw.get('編號'))
    valid_id=bool(re.fullmatch(r'[A-Z0-9]{8,40}',serial)) and not serial.startswith(('DEMO','SAMPLE','SYNTHETIC'))
    has_note=bool(text(raw.get('備註')))
    # Preserve every source field in the version hash, including notes and serial.
    semantic={k:text(v) for k,v in raw.items()}
    semantic_sha=sha(canonical(semantic))
    day=parse_roc_date(text(raw.get('交易年月日')))
    exact_day=day['value'] if day and day['precision']=='day' else None
    area=_decimal(raw.get('建物移轉總面積平方公尺'))
    price=_decimal(raw.get('總價元'))
    unit=_decimal(raw.get('單價元平方公尺'))
    # Independent, full-precision facts. No legacy dedupe_key is used or stored.
    facts={k:re.sub(r'\s+','',semantic.get(k,'')) for k in ('鄉鎮市區','土地位置建物門牌','建物型態','移轉層次')}
    known_floor=parse_floor(text(raw.get('移轉層次')))
    if known_floor is not None:facts['移轉層次']=str(known_floor)
    facts.update(city=FILE_CITY_MAP[county],day=exact_day or semantic.get('交易年月日',''),
                 area=_number_string(area),price=_number_string(price))
    fact=sha(canonical(facts))
    reason=None
    if not valid_id:
        reason=('sample_demo_transaction' if serial.startswith(('DEMO','SAMPLE','SYNTHETIC')) else 'missing_official_serial' if not serial else 'invalid_official_serial')
    elif not exact_day:reason='invalid_transaction_day'
    elif exact_day>as_of:reason='future_transaction_date'
    elif area is None or price is None or area<=0 or price<=0:reason='invalid_numeric_facts'
    elif text(raw.get('單價元平方公尺')) and (unit is None or unit<=0):reason='invalid_official_unit_price'
    normalized=None
    if reason is None:
        try:
            normalized,reason=normalize_row(raw,city_hint=FILE_CITY_MAP[county],as_of=date.fromisoformat(as_of),allow_official_city_level=True)
        except (ValueError,OverflowError,InvalidOperation):reason='normalization_failed'
        if normalized is not None and any(not math.isfinite(normalized[k]) for k in ('area_ping','total_price','unit_price_per_ping')):
            reason='invalid_numeric_facts';normalized=None
    features=None
    if not reason and normalized is not None:
        floor=parse_floor(text(raw.get('移轉層次')))
        total_floor=parse_floor(text(raw.get('總樓層數')))
        age_evidence=age_at_transaction(text(raw.get('交易年月日')),text(raw.get('建築完成年月')))
        age=age_evidence['age_months'] if age_evidence else None
        parking_count=parse_counts(text(raw.get('交易筆棟數')))
        features={'transaction_date':exact_day,'transaction_period':exact_day[:7],
          'city':normalized['city'],'district':normalized['district'],
          'geographic_unit_kind':normalized['geographic_unit_kind'],'road':normalized['road'],
          'address_sha256':sha(text(raw.get('土地位置建物門牌')).encode()),
          'building_type':normalized['building_type'],'main_use':text(raw.get('主要用途')) or None,
          'area_sqm':_number_string(area),'area_ping':_number_string(area*Decimal('0.3025')),
          'total_price_ntd':_number_string(price),
          'gross_unit_price_ntd_ping':_number_string(price/(area*Decimal('0.3025'))),
          'official_unit_price_ntd_sqm':_number_string(unit),
          'production_unit_price_wan_ping':normalized['unit_price_per_ping'],
          'floor':floor,'total_floor':total_floor,'building_age_months_at_transaction':age,
          'parking_count_reported':parking_count[2] if parking_count else None,
          'parking_basis':'UNVERIFIED','rights_status':'UNVERIFIED',
          'ordinary_sale_status':'NO_REPORTED_NOTE_NOT_PROOF_OF_ARMS_LENGTH',
          'source_release_available_at':None,'historical_publication_proven':False,
          'training_authorized':False}
    return {'official_id':serial if valid_id else None,'semantic_sha256':semantic_sha,
      'raw_row_sha256':sha(canonical(raw)),'fact_key':fact,'has_note':has_note,
      'quality_reason':reason,'features':features,'transaction_date':exact_day}


def _safe_child(root, relative):
    p=PurePosixPath(relative)
    if p.is_absolute() or '..' in p.parts or '\\' in relative or not p.parts:raise ValueError('unsafe_source_member')
    path=root.joinpath(*p.parts)
    if any(x.is_symlink() for x in [path,*path.parents] if x!=root.parent) or not path.resolve().is_relative_to(root.resolve()):
        raise ValueError('source_symlink_disallowed')
    return path


def releases(root, expected_releases, county_codes):
    manifest=root/'00_manifest/plvr_10y_40q_manifest.csv'
    with open_source(manifest) as f:
        rows=list(csv.DictReader(io.TextIOWrapper(f,encoding='utf-8-sig',newline='')))
    if len(rows)!=expected_releases:raise ValueError('release_count_mismatch')
    result=[];seen=set()
    for r in rows:
        season=r.get('Season','');m=RELEASE_RE.fullmatch(season)
        filename=f'plvr_{season}_lvr_landcsv.zip'
        digest=r.get('SHA256','').lower()
        if not m or season in seen or r.get('Filename')!=filename or not re.fullmatch('[0-9a-f]{64}',digest) or r.get('Status')!='PASS':
            raise ValueError('release_manifest_invalid')
        if int(r['Sale_A'])!=len(county_codes):raise ValueError('release_county_count_mismatch')
        seen.add(season)
        result.append({**r,'sha256':digest,'release':season,'ordinal':int(m[1])*4+int(m[2])-1})
    result.sort(key=lambda x:x['ordinal'])
    if any(b['ordinal']!=a['ordinal']+1 for a,b in zip(result,result[1:])):raise ValueError('release_gap')
    actual={p.name for p in (root/'01_raw_zip').iterdir() if p.is_file()}
    if actual!={r['Filename'] for r in result}:raise ValueError('unmanifested_archive')
    return result


def _initialize(db):
    db.executescript('''
    pragma journal_mode=DELETE; pragma synchronous=NORMAL;
    pragma temp_store=FILE; pragma cache_size=-32768; pragma threads=1;
    create table source_files(file_id text primary key, release text, member text, sha256 text,
       archive_sha256 text, size integer, role text, row_count integer, schema_sha256 text);
    create table occurrences(occurrence_id text primary key, official_id text, semantic_sha256 text,
       raw_row_sha256 text, fact_key text, file_id text, record_number integer,
       physical_start integer, physical_end integer, has_note integer, quality_reason text);
    create table versions(official_id text, semantic_sha256 text, fact_key text,
       representative text, features_json text, quality_reason text,
       primary key(official_id,semantic_sha256));
    ''')


def _walk_csv(data, county, as_of):
    reader=csv.reader(io.StringIO(data.decode('utf-8-sig',errors='strict'),newline=''),strict=True)
    header=next(reader,None)
    if not header or len(set(header))!=len(header) or not set(REQUIRED)<=set(header):raise ValueError('main_schema_invalid')
    prior=reader.line_num;description=next(reader,None)
    labels={'鄉鎮市區':'the villages and towns urban district','交易標的':'transaction sign',
            '交易年月日':'transaction year month and day','編號':'serial number','總價元':'total price ntd'}
    if (not description or len(description)!=len(header)
            or any(text(description[header.index(k)]).casefold()!=v for k,v in labels.items())):
        raise ValueError('english_descriptor_missing')
    schema=sha(canonical(header));prior=reader.line_num
    for record,cells in enumerate(reader,3):
        start=prior+1;prior=reader.line_num
        if len(cells)!=len(header):raise ValueError('csv_field_count')
        raw=dict(zip(header,cells))
        yield record,start,prior,schema,row_evidence(raw,county,as_of)


def _audit_ingest(root, db, specs, counties, as_of, progress):
    manifest=[];counts=Counter();raw_quality=Counter();raw_months=Counter();raw_range=[None,None]
    for release in specs:
        if shutil.disk_usage(Path(db.execute('pragma database_list').fetchone()[2]).parent).free<8*1024**3:
            raise ValueError('disk_reserve_low')
        path=_safe_child(root,'01_raw_zip/'+release['Filename'])
        if path.stat().st_size!=int(release['Bytes']) or hash_file(path)!=release['sha256']:raise ValueError('archive_checksum_mismatch')
        with open_source(path) as rawzip,zipfile.ZipFile(rawzip) as z:
            infos=z.infolist();names=[x.filename for x in infos]
            if len(infos)>MAX_MEMBERS or len(names)!=len(set(names)) or len(infos)!=int(release['Entries']):raise ValueError('archive_members_invalid')
            expected={c+'_lvr_land_a.csv' for c in counties}
            if {n for n in names if MAIN_RE.fullmatch(n)}!=expected:raise ValueError('sale_members_mismatch')
            extracted=root/'02_extracted'/release['release']
            actual={str(p.relative_to(extracted)) for p in extracted.rglob('*') if p.is_file()}
            if actual!=set(names):raise ValueError('extracted_members_mismatch')
            release_rows=0
            for info in sorted(infos,key=lambda x:x.filename):
                name=info.filename
                if info.is_dir() or info.file_size>MAX_MEMBER or info.flag_bits&1 or stat.S_IFMT(info.external_attr>>16)==stat.S_IFLNK:
                    raise ValueError('archive_member_unsupported')
                original=_safe_child(extracted,name)
                with z.open(info) as stream:
                    h=hashlib.sha256();chunks=[] if MAIN_RE.fullmatch(name) else None
                    while chunk:=stream.read(1024*1024):
                        h.update(chunk)
                        if chunks is not None:chunks.append(chunk)
                digest=h.hexdigest()
                if original.stat().st_size!=info.file_size or hash_file(original)!=digest:raise ValueError('extracted_member_mismatch')
                match=MAIN_RE.fullmatch(name)
                role='sale_main' if match else 'presale' if re.fullmatch('[a-z]_lvr_land_b.*',name) else 'rent' if re.fullmatch('[a-z]_lvr_land_c.*',name) else 'detail_or_schema'
                fid=sha(canonical([release['release'],release['sha256'],name,digest]))
                entry={'file_id':fid,'release':release['release'],'member':name,'sha256':digest,
                  'archive_sha256':release['sha256'],'size':info.file_size,'role':role,'row_count':0,'schema_sha256':None}
                if match:
                    for number,start,end,schema,e in _walk_csv(b''.join(chunks),match[1],as_of):
                        entry['row_count']+=1;entry['schema_sha256']=schema
                        counts['raw_sale_rows']+=1;release_rows+=1
                        raw_quality[e['quality_reason'] or 'production_eligible']+=1
                        if e['transaction_date']:
                            day=e['transaction_date'];raw_months[day[:7]]+=1
                            raw_range[0]=min(raw_range[0] or day,day);raw_range[1]=max(raw_range[1] or day,day)
                        occ=sha(canonical([fid,number,e['raw_row_sha256']]))
                        db.execute('insert into occurrences values (?,?,?,?,?,?,?,?,?,?,?)',
                          (occ,e['official_id'],e['semantic_sha256'],e['raw_row_sha256'],e['fact_key'],fid,number,start,end,int(e['has_note']),e['quality_reason']))
                        if e['official_id']:
                            payload=canonical(e['features']).decode() if e['features'] and not e['has_note'] else None
                            db.execute('''insert into versions values (?,?,?,?,?,?) on conflict(official_id,semantic_sha256)
                              do update set representative=min(representative,excluded.representative)''',
                              (e['official_id'],e['semantic_sha256'],e['fact_key'],occ,payload,e['quality_reason']))
                    counts['sale_main_files']+=1
                db.execute('insert into source_files values (?,?,?,?,?,?,?,?,?)',tuple(entry[k] for k in ('file_id','release','member','sha256','archive_sha256','size','role','row_count','schema_sha256')))
                manifest.append(entry);counts['all_archive_members']+=1
            db.commit()
            if progress:progress({'phase':'audit_ingest','release':release['release'],'release_rows':release_rows,'raw_sale_rows':counts['raw_sale_rows']})
    return manifest,counts,raw_quality,raw_months,raw_range


def _select(db):
    db.executescript('''
    create index occurrences_identity on occurrences(official_id);
    create index occurrences_fact on occurrences(fact_key,official_id);
    create table identity_stats as select official_id,count(*) n, count(distinct semantic_sha256) versions,
       max(has_note) has_note from occurrences where official_id is not null group by official_id;
    create unique index identity_stats_id on identity_stats(official_id);
    create table fact_stats as select fact_key,count(distinct official_id) ids,max(has_note) has_note
       from occurrences group by fact_key;
    create unique index fact_stats_key on fact_stats(fact_key);
    create table dispositions(official_id text primary key, reason text, version_count integer);
    create table clean_transactions(canonical_id text primary key,official_id text unique,semantic_sha256 text,
       fact_key text,representative text,transaction_date text,city text,district text,building_type text,features_json text);
    ''')
    counts=Counter()
    cursor=db.execute('''select i.official_id,i.n,i.versions,i.has_note,v.semantic_sha256,v.fact_key,
      v.representative,v.features_json,v.quality_reason,f.ids,f.has_note
      from identity_stats i join versions v on v.official_id=i.official_id
      join fact_stats f on f.fact_key=v.fact_key order by i.official_id,v.semantic_sha256''')
    last=None
    for serial,n,versions,note,semantic,fact,representative,payload,quality,ids,fact_note in cursor:
        if serial==last:continue
        last=serial
        reason=('known_related_party_serial' if serial==KNOWN_SERIAL else
                'special_note_requires_review' if note else
                'ambiguous_special_note_match' if fact_note else
                'ambiguous_revision' if versions!=1 else
                'ambiguous_fact_identity' if ids!=1 else quality)
        db.execute('insert into dispositions values (?,?,?)',(serial,reason,versions))
        if reason:counts[reason]+=1;continue
        features=json.loads(payload)
        cid=sha(('moi-plvr-sale-a|'+serial).encode())
        db.execute('insert into clean_transactions values (?,?,?,?,?,?,?,?,?,?)',
          (cid,serial,semantic,fact,representative,features['transaction_date'],features['city'],features['district'],features['building_type'],payload))
    db.commit()
    return counts


def _json_file(path,value):
    with path.open('xb') as f:f.write(canonical(value)+b'\n')


def validate_output(root, parent):
    root=Path(root).resolve();parent=Path(parent).resolve()
    if (parent.is_relative_to(root) or any(parent.is_relative_to(x) for x in FORBIDDEN_OUTPUT)
            or parent.is_relative_to(Path('/dev')) or parent.is_relative_to(Path(__file__).resolve().parents[1])):
        raise ValueError('unsafe_output')


def _schema():
    return {'schema_version':VERSION,'format':'gzip JSON Lines, UTF-8, stable canonical_id order',
      'identity':'sha256(moi-plvr-sale-a|official_serial); official serial retained; strong facts and revisions quarantined',
      'units':{'area_sqm':'m2 reported transferred building area','area_ping':'area_sqm * 0.3025',
        'total_price_ntd':'NTD reported consideration','gross_unit_price_ntd_ping':'total consideration / reported gross transferred ping; NOT a no-parking/whole-dwelling target',
        'official_unit_price_ntd_sqm':'unmodified reported source unit price','production_unit_price_wan_ping':'legacy normalizer gate output in 10000 NTD/ping',
        'building_age_months_at_transaction':'completed month to transaction month; unknown null'},
      'required_row_fields':['canonical_id','official_serial','semantic_sha256','fact_sha256','provenance',
        'transaction_date','transaction_period','city','district','building_type','area_sqm','area_ping','total_price_ntd',
        'gross_unit_price_ntd_ping','source_release_available_at','historical_publication_proven','training_authorized'],
      'nullable_unproven':['floor','total_floor','building_age_months_at_transaction','parking_count_reported',
        'main_use','official_unit_price_ntd_sqm','source_release_available_at'],
      'privacy':'No full raw addresses, personal identity, notes or credential material retained. Source locators permit authorized raw inspection.',
      'training_authorized':False,'publication_policy':'Quarter, transaction date and file mtime are NOT publication evidence.',
      'record_json_schema':{'$schema':'https://json-schema.org/draft/2020-12/schema','type':'object',
        'required':['canonical_id','official_serial','semantic_sha256','fact_sha256','provenance','transaction_date',
          'city','district','building_type','area_sqm','area_ping','total_price_ntd','gross_unit_price_ntd_ping',
          'source_release_available_at','historical_publication_proven','training_authorized'],
        'properties':{'canonical_id':{'type':'string','pattern':'^[0-9a-f]{64}$'},
          'official_serial':{'type':'string','pattern':'^[A-Z0-9]{8,40}$'},
          'semantic_sha256':{'type':'string','pattern':'^[0-9a-f]{64}$'},
          'fact_sha256':{'type':'string','pattern':'^[0-9a-f]{64}$'},
          'transaction_date':{'type':'string','format':'date'},
          'source_release_available_at':{'type':'null'},'historical_publication_proven':{'const':False},
          'training_authorized':{'const':False},'provenance':{'type':'object'}}}}



def _export(db,folder):
    logical=hashlib.sha256();count=0
    cursor=db.execute('''select c.*,o.file_id,o.record_number,o.physical_start,o.physical_end,o.raw_row_sha256,
      f.release,f.member from clean_transactions c join occurrences o on o.occurrence_id=c.representative
      join source_files f on f.file_id=o.file_id order by c.canonical_id''')
    with (folder/'transactions.jsonl.gz').open('xb') as out,gzip.GzipFile(filename='',fileobj=out,mode='wb',compresslevel=3,mtime=0) as gz:
        for cid,serial,semantic,fact,rep,day,city,district,btype,payload,fid,number,start,end,rawhash,release,member in cursor:
            row={**json.loads(payload),'canonical_id':cid,'official_serial':serial,'semantic_sha256':semantic,'fact_sha256':fact,
              'provenance':{'representative_occurrence_id':rep,'file_id':fid,'release':release,'member':member,
                'record_number':number,'physical_start':start,'physical_end':end,'raw_row_sha256':rawhash}}
            raw=canonical(row)+b'\n';logical.update(raw);gz.write(raw);count+=1
    return count,logical.hexdigest()


def build_dataset(source_root,output_parent,*,as_of,expected_releases=40,county_codes=None,progress=None):
    started=time.monotonic()
    root=Path(source_root).resolve(strict=True);parent=Path(output_parent).resolve()
    as_of=date.fromisoformat(as_of).isoformat()
    validate_output(root,parent)
    existing=parent
    while not existing.exists():existing=existing.parent
    if shutil.disk_usage(existing).free<16*1024**3:raise ValueError('insufficient_disk')
    os.umask(0o077);parent.mkdir(parents=True,exist_ok=True,mode=0o700)
    folder=parent/('.building-'+uuid.uuid4().hex);folder.mkdir(mode=0o700)
    specs=releases(root,expected_releases,county_codes or tuple(sorted(FILE_CITY_MAP)))
    os.environ['SQLITE_TMPDIR']=str(folder)
    db=sqlite3.connect(folder/'lineage.sqlite');_initialize(db)
    try:
        manifest,counts,raw_quality,raw_months,raw_range=_audit_ingest(root,db,specs,county_codes or tuple(sorted(FILE_CITY_MAP)),as_of,progress)
        if progress:progress({'phase':'identity_selection','raw_sale_rows':counts['raw_sale_rows']})
        excluded=_select(db)
        scalar=lambda q:db.execute(q).fetchone()[0]
        counts.update(canonical_identities=scalar('select count(*) from identity_stats'),
          unique_semantic_versions=scalar('select count(*) from versions'),
          unidentified_occurrences=scalar('select count(*) from occurrences where official_id is null'),
          conflicting_identity_groups=scalar('select count(*) from identity_stats where versions>1'))
        counts['duplicate_occurrences_removed']=counts['raw_sale_rows']-counts['unidentified_occurrences']-counts['unique_semantic_versions']
        counts['revision_versions_quarantined']=counts['unique_semantic_versions']-counts['canonical_identities']
        counts['excluded_identities']=sum(excluded.values())
        count,logical=_export(db,folder);counts['clean_transactions']=count
        invalid=db.execute('''select count(*) from clean_transactions c
          join identity_stats i using(official_id) join fact_stats f on f.fact_key=c.fact_key
          join occurrences o on o.occurrence_id=c.representative
          where i.versions<>1 or i.has_note<>0 or f.ids<>1 or f.has_note<>0
             or o.has_note<>0 or o.quality_reason is not null''').fetchone()[0]
        if invalid:raise ValueError('clean_selection_invariant')

        if expected_releases==40 and not count:raise ValueError('empty_clean_archive')
        assert counts['canonical_identities']==count+counts['excluded_identities']
        assert counts['raw_sale_rows']==counts['unidentified_occurrences']+counts['duplicate_occurrences_removed']+counts['unique_semantic_versions']
        coverage={key:[{'key':list(values[:-1]),'rows':values[-1]} for values in db.execute(query)] for key,query in {
          'city_district':'select city,district,count(*) from clean_transactions group by city,district order by city,district',
          'building_type':'select building_type,count(*) from clean_transactions group by building_type order by building_type',
          'monthly':'select substr(transaction_date,1,7),count(*) from clean_transactions group by 1 order by 1'}.items()}
        clean_range=db.execute('select min(transaction_date),max(transaction_date) from clean_transactions').fetchone()
        known=db.execute('select reason,version_count from dispositions where official_id=?',(KNOWN_SERIAL,)).fetchone()
        if expected_releases==40 and (known is None or known[0]!='known_related_party_serial'):
            raise ValueError('known_special_serial_invariant')
        duplicate_archives=[{'sha256':h,'releases':[s['release'] for s in specs if s['sha256']==h]} for h,n in Counter(s['sha256'] for s in specs).items() if n>1]
        code_root=Path(__file__).resolve().parents[1]
        code_hashes={name:hash_file(code_root/name) for name in ('services/plvr_historical_dataset.py','services/plvr_import_service.py','services/plvr_data_integrity.py','services/taiwan_admin_registry.py','scripts/ml/semantics.py','data/taiwan-admin-areas.json')}
        fingerprint=sha(canonical({'version':VERSION,'as_of':as_of,'logical':logical,'code':code_hashes,
          'sources':[(x['release'],x['sha256']) for x in specs],
          'normalizer':hash_file(Path(__file__).with_name('plvr_import_service.py')),
          'builder':hash_file(Path(__file__))}))
        record_schema=_schema()
        props=record_schema['record_json_schema']['properties']
        for key in ('transaction_period','city','district','geographic_unit_kind','road','address_sha256',
                    'building_type','area_sqm','area_ping','total_price_ntd','gross_unit_price_ntd_ping',
                    'parking_basis','rights_status','ordinary_sale_status'):
            props[key]={'type':'string'}
        for key in ('main_use','official_unit_price_ntd_sqm'):
            props[key]={'type':['string','null']}
        for key in ('floor','total_floor','building_age_months_at_transaction','parking_count_reported'):
            props[key]={'type':['integer','null']}
        props['production_unit_price_wan_ping']={'type':'number','exclusiveMinimum':0}
        record_schema['record_json_schema']['required']=sorted(props)
        record_schema['record_json_schema']['additionalProperties']=False
        _json_file(folder/'schema.json',record_schema)
        _json_file(folder/'coverage.json',coverage)
        _json_file(folder/'provenance-manifest.json',{'schema':VERSION,'actual_source_root':str(root),
          'intended_server_root':'/srv/proptech-data/DB/實價登錄 PLVR','server_copy_read_verified_this_run':str(root).startswith('/srv/proptech-data/DB/'),
          'source_manifest_sha256':hash_file(root/'00_manifest/plvr_10y_40q_manifest.csv'),
          'as_of':as_of,'transform_code_sha256':code_hashes,'source_publication_times_proven':False,'releases':[{k:s[k] for k in ('release','sha256','Filename','Bytes','Entries')} for s in specs],
          'members':manifest,'duplicate_archive_hashes':duplicate_archives})
        db.execute('create index clean_transaction_day on clean_transactions(transaction_date)')
        db.execute('create index clean_geography on clean_transactions(city,district)')
        unidentified_reasons=dict(db.execute('select quality_reason,count(*) from occurrences where official_id is null group by quality_reason'))
        check=db.execute('pragma integrity_check').fetchone()[0]
        assert check=='ok';db.commit();db.close();db=None
        result={'schema':VERSION,'status':'PASS','scope':'canonical offline historical staging; not point-in-time training authorization',
          'as_of':as_of,'counts':dict(counts),'exclusions_by_reason':dict(sorted(excluded.items())),
          'raw_quality_reasons':dict(sorted(raw_quality.items())), 'unidentified_exclusions_by_reason':unidentified_reasons, 'raw_transaction_months':dict(sorted(raw_months.items())),
          'release_window':[specs[0]['release'],specs[-1]['release']],'release_count':len(specs),
          'raw_valid_calendar_date_range':raw_range,'clean_transaction_date_range':list(clean_range),'dataset_fingerprint':fingerprint,
          'logical_dataset_sha256':logical,'dataset_gzip_sha256':hash_file(folder/'transactions.jsonl.gz'),
          'known_special_serial':{'serial':KNOWN_SERIAL,'present_in_raw':known is not None,'excluded':known is not None and known[0]=='known_related_party_serial','reason':known[0] if known else None},
          'training_authorized':False,'temporal_and_target_gates':'Existing strict ML gates unchanged; no publication, rights, parking, complete revision/cancellation certificate inferred.',
          'integrity':{'sqlite':'ok','counts_reconcile':True,'zip_crc_and_extracted_sha256':'PASS','raw_source_modified':False},
          'artifact_hashes':{n:hash_file(folder/n) for n in ('lineage.sqlite','transactions.jsonl.gz','schema.json','coverage.json','provenance-manifest.json')},
          'actual_source_root':str(root),
          'resource_usage':{'elapsed_seconds':round(time.monotonic()-started,3),'peak_rss_bytes':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024,'sqlite_cache_bytes':32*1024**2,'workers':1,'sqlite_temp_store':'FILE under new staging directory'}}
        if len(coverage['monthly']):
            runs=[];current=[];previous=None
            for item in coverage['monthly']:
                month=item['key'][0];ordinal=int(month[:4])*12+int(month[5:])-1
                if item['rows']<100 or previous is not None and ordinal!=previous+1:
                    if current:runs.append(current)
                    current=[]
                if item['rows']>=100:current.append(item)
                previous=ordinal
            if current:runs.append(current)
            longest=max(runs,key=lambda r:(len(r),sum(x['rows'] for x in r))) if runs else []
            result['longest_dense_calendar_window']={'minimum_rows_per_month':100,'months':len(longest),
              'from':longest[0]['key'][0] if longest else None,'through':longest[-1]['key'][0] if longest else None,
              'rows':sum(x['rows'] for x in longest),'historical_completeness_proven':False}
        _json_file(folder/'summary.json',result)
        _json_file(folder/'COMPLETE.json',{'dataset_fingerprint':fingerprint,'summary_sha256':hash_file(folder/'summary.json')})
        final=parent/fingerprint
        if final.exists():raise ValueError('immutable_dataset_already_exists')
        folder.rename(final)
        for p in final.iterdir():p.chmod(0o440)
        final.chmod(0o550)
        return {**result,'artifact_dir':str(final)}
    finally:
        if db is not None:db.close()


def _validate_record(row,schema,source_files,as_of):
    properties=schema['record_json_schema']['properties']
    if set(row)!=set(properties):raise ValueError('record_schema_fields')
    kinds={'string':str,'integer':int,'number':(int,float),'object':dict,'null':type(None)}
    for key,contract in properties.items():
        value=row[key]
        if 'const' in contract and value is not contract['const']:raise ValueError('record_schema_constant')
        if 'type' in contract:
            types=contract['type'] if isinstance(contract['type'],list) else [contract['type']]
            if not any(isinstance(value,kinds[k]) and not (isinstance(value,bool) and k in {'integer','number'}) for k in types):
                raise ValueError('record_schema_type')
    for key in ('canonical_id','semantic_sha256','fact_sha256','address_sha256'):
        if not re.fullmatch('[0-9a-f]{64}',row[key]):raise ValueError('record_digest_shape')
    if (not re.fullmatch('[A-Z0-9]{8,40}',row['official_serial'])
            or row['canonical_id']!=sha(('moi-plvr-sale-a|'+row['official_serial']).encode())
            or row['official_serial']==KNOWN_SERIAL):raise ValueError('record_identity')
    day=date.fromisoformat(row['transaction_date']).isoformat()
    if day!=row['transaction_date'] or day>as_of or row['transaction_period']!=day[:7]:raise ValueError('record_date')
    if (row['training_authorized'] is not False or row['historical_publication_proven'] is not False
            or row['source_release_available_at'] is not None):raise ValueError('training_authorization_invented')
    unit=row['production_unit_price_wan_ping']
    if not math.isfinite(unit) or not 1<=unit<=500:raise ValueError('production_price_invariant')
    for key in ('floor','total_floor'):
        if row[key] is not None and not 1<=row[key]<=100:raise ValueError('floor_invariant')
    for key in ('building_age_months_at_transaction','parking_count_reported'):
        if row[key] is not None and row[key]<0:raise ValueError('optional_integer_invariant')
    area,ping,price,gross=(_decimal(row[k]) for k in ('area_sqm','area_ping','total_price_ntd','gross_unit_price_ntd_ping'))
    if (any(x is None or x<=0 for x in (area,ping,price,gross)) or ping!=area*Decimal('0.3025')
            or gross!=price/ping):raise ValueError('record_arithmetic')
    proof=row['provenance'];source=source_files.get(proof['file_id'])
    if (not source or source['role']!='sale_main' or proof['release']!=source['release'] or proof['member']!=source['member']
            or type(proof['record_number']) is not int or not 3<=proof['record_number']<=source['row_count']+2
            or proof['physical_start']<proof['record_number'] or proof['physical_end']<proof['physical_start']
            or not re.fullmatch('[0-9a-f]{64}',proof['raw_row_sha256'])
            or proof['representative_occurrence_id']!=sha(canonical([proof['file_id'],proof['record_number'],proof['raw_row_sha256']]))):
        raise ValueError('record_provenance')


def verify_artifact(folder):
    folder=Path(folder);complete=json.loads((folder/'COMPLETE.json').read_text())
    if hash_file(folder/'summary.json')!=complete['summary_sha256']:raise ValueError('summary_checksum_mismatch')
    summary=json.loads((folder/'summary.json').read_text())
    for name,expected in summary['artifact_hashes'].items():
        if name not in {'lineage.sqlite','transactions.jsonl.gz','schema.json','coverage.json','provenance-manifest.json'} or hash_file(folder/name)!=expected:
            raise ValueError('artifact_checksum_mismatch')
    if summary['schema']!=VERSION or summary['training_authorized'] is not False:raise ValueError('artifact_contract')
    schema=json.loads((folder/'schema.json').read_text())
    manifest=json.loads((folder/'provenance-manifest.json').read_text())
    files={x['file_id']:x for x in manifest['members']}
    logical=hashlib.sha256();count=0;last=''
    with sqlite3.connect((folder/'lineage.sqlite').resolve().as_uri()+'?mode=ro&immutable=1',uri=True) as db:
        db.execute('pragma query_only=ON')
        if db.execute('pragma integrity_check').fetchone()!=('ok',):raise ValueError('sqlite_integrity')
        db_files={x[0]:x for x in db.execute('select file_id,release,member,sha256,archive_sha256,size,role,row_count,schema_sha256 from source_files')}
        if set(db_files)!=set(files):raise ValueError('source_manifest_sqlite_mismatch')
        for fid,source in files.items():
            if db_files[fid]!=tuple(source[k] for k in ('file_id','release','member','sha256','archive_sha256','size','role','row_count','schema_sha256')):
                raise ValueError('source_manifest_sqlite_mismatch')
        cursor=db.execute('''select c.canonical_id,c.official_id,c.semantic_sha256,c.fact_key,c.representative,c.features_json,
          o.file_id,o.record_number,o.physical_start,o.physical_end,o.raw_row_sha256
          from clean_transactions c left join occurrences o on o.occurrence_id=c.representative order by c.canonical_id''')
        with open_source(folder/'transactions.jsonl.gz') as raw,gzip.GzipFile(fileobj=raw) as gz:
            for line in gz:
                value=json.loads(line);_validate_record(value,schema,files,summary['as_of'])
                stored=cursor.fetchone()
                if (value['canonical_id']<=last or stored is None
                        or stored[:5]!=(value['canonical_id'],value['official_serial'],value['semantic_sha256'],value['fact_sha256'],value['provenance']['representative_occurrence_id'])):
                    raise ValueError('canonical_row_invariant')
                payload={k:v for k,v in value.items() if k not in {'canonical_id','official_serial','semantic_sha256','fact_sha256','provenance'}}
                if payload!=json.loads(stored[5]):raise ValueError('sqlite_jsonl_content_mismatch')
                if stored[6:]!=tuple(value['provenance'][k] for k in ('file_id','record_number','physical_start','physical_end','raw_row_sha256')):
                    raise ValueError('sqlite_provenance_mismatch')
                last=value['canonical_id'];logical.update(line);count+=1
        if cursor.fetchone() is not None:raise ValueError('missing_jsonl_rows')
        if count!=summary['counts']['clean_transactions'] or logical.hexdigest()!=summary['logical_dataset_sha256']:raise ValueError('logical_dataset_mismatch')
        scalar=lambda q:db.execute(q).fetchone()[0]
        if scalar('select count(*) from occurrences')!=summary['counts']['raw_sale_rows']:raise ValueError('raw_count_mismatch')
        if scalar('select count(*) from dispositions')!=summary['counts']['canonical_identities']:raise ValueError('identity_count_mismatch')
        if scalar('select count(*) from occurrences o left join source_files f using(file_id) where f.file_id is null'):raise ValueError('orphan_provenance')
        bad=scalar('''select count(*) from clean_transactions c left join dispositions d using(official_id)
          left join identity_stats i using(official_id) left join fact_stats f on f.fact_key=c.fact_key
          left join occurrences o on o.occurrence_id=c.representative
          where d.official_id is null or i.official_id is null or f.fact_key is null or o.occurrence_id is null
            or d.reason is not null or i.versions<>1 or i.has_note<>0 or f.ids<>1 or f.has_note<>0
            or o.has_note<>0 or o.quality_reason is not null''')
        if bad:raise ValueError('exclusion_leak')
        actual=dict(db.execute('select reason,count(*) from dispositions where reason is not null group by reason'))
        if actual!=summary['exclusions_by_reason']:raise ValueError('exclusion_count_mismatch')
    hashes=manifest['transform_code_sha256']
    fingerprint=sha(canonical({'version':VERSION,'as_of':summary['as_of'],'logical':logical.hexdigest(),'code':hashes,
      'sources':[(x['release'],x['sha256']) for x in manifest['releases']],
      'normalizer':hashes['services/plvr_import_service.py'],'builder':hashes['services/plvr_historical_dataset.py']}))
    if fingerprint!=summary['dataset_fingerprint'] or fingerprint!=complete['dataset_fingerprint']:raise ValueError('dataset_fingerprint_mismatch')
    return {'status':'PASS','clean_transactions':count,'dataset_fingerprint':fingerprint,
            'logical_dataset_sha256':logical.hexdigest(),'training_authorized':False}


def verify_source(folder,source_root):
    """Optional operator read-only comparison with the protected server copy."""
    manifest=json.loads((Path(folder)/'provenance-manifest.json').read_text());root=Path(source_root).resolve(strict=True)
    for release in manifest['releases']:
        if hash_file(_safe_child(root,'01_raw_zip/'+release['Filename']))!=release['sha256']:raise ValueError('source_archive_mismatch')
    for item in manifest['members']:
        if hash_file(_safe_child(root,'02_extracted/'+item['release']+'/'+item['member']))!=item['sha256']:raise ValueError('source_member_mismatch')
    return {'status':'PASS','releases':len(manifest['releases']),'members':len(manifest['members']),'source_changed':False}
