"""Minimized synthetic fixtures; raw official rows never enter Git."""
import importlib

import pytest

from scripts.ml import semantics as s


def parser():
    assert importlib.util.find_spec('scripts.ml.plvr_raw_parser') is not None, 'strict raw parser required'
    return importlib.import_module('scripts.ml.plvr_raw_parser')


def raw(**changes):
    item = {'交易標的':'房地(土地+建物)', '交易筆棟數':'土地1建物1車位0',
            '車位類別':'', '車位總價元':'0', '車位移轉總面積平方公尺':'0'}
    item.update(changes)
    return item


@pytest.mark.parametrize('changes,parks,builds,complete,unique,want', [
    ({}, [], [{'主要用途':'住家用'}], True, True, 'NO_PARKING_CONFIRMED'),
    ({'交易筆棟數':'土地1建物1車位1'}, [{'車位類別':'坡道平面'}], [], True, True, 'PARKING_PRESENT'),
    ({'交易筆棟數':'土地1建物1車位2'}, [{},{}], [], True, True, 'PARKING_PRESENT'),
    ({'車位總價元':'100'}, [], [], True, True, 'PARKING_PRESENT'),
    ({'車位移轉總面積平方公尺':'2'}, [], [], True, True, 'PARKING_PRESENT'),
    ({}, [], [{'主要用途':'住家用'}], False, True, 'UNKNOWN'),
    ({}, [], [], True, True, 'UNKNOWN'),
    ({}, [], [{'主要用途':'住家用'}], True, False, 'PARKING_SEMANTICS_AMBIGUOUS'),
    ({}, [{'車位類別':'坡道平面'}], [], True, True, 'PARKING_SEMANTICS_AMBIGUOUS'),
    ({}, [], [{'主要用途':'共有部分含停車空間'}], True, True, 'PARKING_SEMANTICS_AMBIGUOUS'),
    ({'車位總價元':''}, [], [{'主要用途':'住家用'}], True, True, 'PARKING_SEMANTICS_AMBIGUOUS'),
    ({'車位移轉總面積平方公尺':'NaN'}, [], [{'主要用途':'住家用'}], True, True, 'PARKING_SEMANTICS_AMBIGUOUS'),
    ({'備註':'車位價款包含於總價內'}, [], [{'主要用途':'住家用'}], True, True, 'PARKING_SEMANTICS_AMBIGUOUS'),
    ({}, [], [{'主要用途':''}], True, True, 'UNKNOWN'),
])
def test_parking_absence_needs_complete_unambiguous_join(changes, parks, builds, complete, unique, want):
    p = parser()
    context = p.unproven_context('a_lvr_land_a.csv','b'*64,'c'*64,len(parks))
    assert p.parking_state(raw(**changes), parks, builds, complete, unique, context=context) == want


def test_csv_preserves_malformed_records_and_multiline_locator():
    p = parser()
    content = '編號,備註\r\nSYNTHETIC-1,"two\nlines"\r\nSYNTHETIC-2\r\n'
    result = p.parse_csv(content.encode('utf8'), ['編號','備註'])
    assert len(result['records']) == 2
    assert result['records'][0]['end_line'] == 3
    assert result['records'][1]['parse_error'] == 'CSV_FIELD_COUNT'
    assert result['records'][1]['cells'] == ['SYNTHETIC-2']


def test_csv_does_not_silently_discard_unknown_ascii_records():
    p = parser()
    result = p.parse_csv(b'id,value\nNOT-A-SCHEMA,unknown\n', ['id','value'])
    assert len(result['records']) == 1
    with pytest.raises(ValueError, match='header_schema_mismatch'):
        p.parse_csv(b'id,id\nx,y\n', ['id','value'])
    with pytest.raises(ValueError, match='csv_encoding'):
        p.parse_csv(b'\xff\xff', ['id'])


def test_missing_rights_proof_cannot_be_manufactured_from_details():
    p = parser()
    context = p.unproven_context('a_lvr_land_a.csv', 'b'*64, 'c'*64, 0)
    assert context['full_rights'] is None
    assert context['one_dwelling'] is None
    assert context['rights_evidence'] is None
    assert context['area_basis'] is None
    assert context['special_transaction'] is None


def test_detail_join_retains_repeated_rows_and_fails_closed_missing_key():
    p = parser()
    rows = [{'raw': {'編號':'SYNTHETIC','車位價格':'1'},'parse_error':None},
            {'raw': {'編號':'SYNTHETIC','車位價格':'1'},'parse_error':None}]
    groups, complete = p.detail_index(rows)
    assert len(groups['SYNTHETIC']) == 2
    assert complete is True
    rows.append({'raw': {'編號':''}, 'parse_error':None})
    assert p.detail_index(rows)[1] is False


def test_offline_funnel_conserves_counts_and_rights_fail_closed():
    assert importlib.util.find_spec('scripts.ml.audit_source_recovery') is not None, 'raw audit required'
    a = importlib.import_module('scripts.ml.audit_source_recovery')
    samples = [{'schema':None, 'identity':None, 'geography':None, 'target':None, 'use':None,
                'type':None, 'rights':'RIGHTS_UNPROVEN', 'dwelling':'DWELLING_UNPROVEN',
                'parking':None, 'price_area':None, 'revision':None, 'pit':'MISSING_AVAILABILITY'},
               {'schema':'CSV_FIELD_COUNT'}]
    funnel, reasons = a.semantic_funnel(samples)
    assert funnel[-1]['accepted_count'] == 0
    assert reasons == ['RIGHTS_UNPROVEN','CSV_FIELD_COUNT']
    for stage in funnel:
        assert stage['input_count'] == stage['accepted_count'] + stage['excluded_count']
        assert sum(stage['reason_breakdown'].values()) == stage['excluded_count']


def test_official_bilingual_description_is_not_a_transaction():
    p = parser()
    import csv
    import io
    # Observed MOI spelling is lowercase; a case typo must not add four rows.
    english = list(p.ENGLISH_MAIN)
    english[18] = 'building present situation pattern - health'
    header = [str(i) for i in range(33)]
    out = io.StringIO(newline='')
    csv.writer(out).writerows([header, english])
    result = p.parse_csv(out.getvalue().encode('utf-8'), header, p.ENGLISH_MAIN)
    assert result['description_record_count'] == 1
    assert result['records'] == []
