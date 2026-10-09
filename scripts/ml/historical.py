"""Strict offline history contracts layered over the existing full-ledger selector.

Evidence inputs are reviewed attestations, not self-authenticating signatures.
Format validation never establishes external authority. No real history
certificate is supplied or manufactured by the ML-A2 builder.
"""
from __future__ import annotations

from collections import Counter, defaultdict

from . import chronology, lineage as l, observed_transaction as b
from . import plvr_raw_parser as p, semantics as s, strict_cohort, temporal as t

VERSION = 'plvr-authoritative-history-selector-v1'
GATE_VERSION = 'ml-data-gate-v2'
EVIDENCE_CLASSES = {'AUTHENTICATED', 'SUPPORTED', 'CURRENT_ONLY', 'UNVERIFIED', 'UNAVAILABLE'}


def publication(item: dict) -> dict:
    record = item.get('publication_evidence')
    if not isinstance(record, dict) or record.get('classification') not in {'AUTHENTICATED', 'SUPPORTED'}:
        return {'available_at': None, 'quality': 'UNKNOWN'}
    return t.resolve_availability(record, item.get('release_id'), item.get('archive_sha256'))


def ledger_digest(items: list[dict]) -> str:
    """Bind full supplied visible events and all semantics; omit no model fields."""
    return l.digest(sorted(items, key=l.canonical_bytes))


def certificate_valid(certificate: dict | None, visible: list[dict], cutoff: str) -> bool:
    cert = certificate if isinstance(certificate, dict) else {}
    if 'certificates' in cert:
        candidates = cert['certificates']
        if not isinstance(candidates, list):
            return False
        matches = [x for x in candidates if isinstance(x, dict) and l.timestamp(x.get('cutoff')) == l.timestamp(cutoff)]
        if len(matches) != 1 or 'certificates' in matches[0]:
            return False
        cert = matches[0]
    return (cert.get('classification') in {'AUTHENTICATED', 'SUPPORTED'}
            and s.evidence_valid(cert.get('evidence'))
            and l.timestamp(cert.get('cutoff')) == l.timestamp(cutoff)
            and cert.get('source_dataset_id') == s.SOURCE_DATASET_ID
            and cert.get('visible_ledger_sha256') == ledger_digest(visible)
            and cert.get('stable_namespace') is True
            and cert.get('complete_revision_cancellation_history') is True
            and cert.get('replacement_links_complete') is True)


def select_as_of(items: list[dict], cutoff: str, *, history_certificate: dict | None) -> dict:
    """Only proven visible versions enter revision selection, before target filtering.

    Unknown availability is excluded and invalidates history certification.
    Proven later versions are excluded before conflicts/revision checks, so
    their attributes and cancellations cannot affect an earlier snapshot.
    A certificate must attest complete history and stable namespace for the
    exact visible event ledger at T. Missing records cannot prove cancellation.
    Cross-family replacements are quarantined pending an authoritative resolver.
    """
    boundary = l.timestamp(cutoff)
    if boundary is None:
        raise ValueError('cutoff_requires_timezone')
    if len(items) > 100000:
        raise ValueError('bounded_main_rows_exceeded')
    visible, future, unknown = [], [], []
    reasons = Counter(); dispositions = []
    for x in items:
        resolved = publication(x)
        when = l.timestamp(resolved.get('available_at'))
        if when is None:
            unknown.append(x)
        elif when > boundary:
            future.append(x)
        else:
            visible.append(x)
    def exclude(xs, reason):
        reasons[reason] += len(xs)
        dispositions.extend({**l.identify(x), 'reason': reason, 'cutoff': boundary.isoformat(),
                             'selected_as_of_cutoff': False} for x in xs)
    exclude(unknown, 'HISTORICAL_AVAILABILITY_UNPROVEN')
    exclude(future, 'after_availability_cutoff')
    original_visible = visible
    if unknown or not certificate_valid(history_certificate, original_visible, cutoff):
        exclude(visible, 'COMPLETE_HISTORY_UNPROVEN')
        visible = []
    # An explicit parent in another namespace cannot safely yield two sales.
    version_families = {l.identify(x)['version_id']: l.identify(x)['transaction_family_id'] for x in visible}
    blocked_families = set()
    for x in visible:
        family = l.identify(x)['transaction_family_id']
        parent = x.get('supersedes_version_id')
        if parent in version_families and version_families[parent] != family:
            blocked_families.update((family, version_families[parent]))
        if x.get('replaces_family_id') is not None:
            blocked_families.update((family, x['replaces_family_id']))
    blocked = [x for x in visible if l.identify(x)['transaction_family_id'] in blocked_families]
    exclude(blocked, 'CROSS_NAMESPACE_REPLACEMENT_UNRESOLVED')
    invalid_event_families = set()
    orphan_event = False
    for x in visible:
        if l.identify(x)['transaction_family_id'] in blocked_families:
            continue
        event = x.get('revision_kind')
        needs_edge = event is not None or x.get('supersedes_version_id') is not None or x.get('cancelled') is True
        if needs_edge and x.get('supersedes_version_id') is None:
            # Without a predecessor/link, the replaced namespace is unknown.
            # No other visible family can be certified unaffected.
            orphan_event = True
        supplied_details = x.get('detail_payload_sha256')
        computed_details = {k: l.digest(v) for k, v in x.get('details', {}).items()}
        if (x.get('cancellation_state_evidenced') is not True
                or (needs_edge and (event not in {'CORRECTION', 'SUPERSESSION', 'CANCELLATION'}
                                    or not s.evidence_valid(x.get('revision_evidence'))))
                or (supplied_details is not None and supplied_details != computed_details)):
            invalid_event_families.add(l.identify(x)['transaction_family_id'])
    if orphan_event:
        invalid_event_families.update(l.identify(x)['transaction_family_id'] for x in visible
                                     if l.identify(x)['transaction_family_id'] not in blocked_families)
    invalid_events = [x for x in visible if l.identify(x)['transaction_family_id'] in invalid_event_families]
    exclude(invalid_events, 'HISTORY_EVENT_UNPROVEN')
    qualified = []
    for x in visible:
        if l.identify(x)['transaction_family_id'] in blocked_families | invalid_event_families:
            continue
        resolved = publication(x)
        # Canonical availability is reconstructed from the bound proof, never
        # trusted from an independently mutable row timestamp.
        qualified.append({**x, 'source_release_available_at': resolved['available_at'],
                          'availability_evidence': x['publication_evidence']['evidence'],
                          'detail_payload_sha256': {
                              **{k: l.digest(v) for k, v in x.get('details', {}).items()},
                              '_join_contract': l.digest([x.get('details_complete'), x.get('main_key_unique'), x.get('parse_error')])}})
    result = l.select_as_of(qualified, cutoff)
    reasons.update(result['excluded_reasons'])
    dispositions.extend(result['dispositions'])
    assert len(items) == len(result['selected']) + sum(reasons.values())
    return {**result, 'input_occurrences': len(items), 'selection_version': VERSION,
            'excluded_reasons': dict(sorted((+reasons).items())),
            'dispositions': sorted(dispositions, key=l.canonical_bytes),
            'historically_supported': len(original_visible),
            'history_certificate_valid': not unknown and certificate_valid(history_certificate, original_visible, cutoff)}


def parking_treatment(item: dict) -> dict:
    raw = item['raw']; details = item.get('details', {})
    context = {**item['context'], 'blank_parking_means_absent': False}
    state = p.parking_state(raw, details.get('park', []), details.get('build', []),
                            item.get('details_complete') is True, item.get('main_key_unique') is True,
                            context=context)
    price, area = (s.number(raw.get(k)) for k in ('車位總價元', '車位移轉總面積平方公尺'))
    counts = s.parse_counts(raw.get('交易筆棟數'))
    if state == 'NO_PARKING_CONFIRMED':
        category = 'NO_PARKING_INCLUDED'
    elif price is None or area is None or counts is None:
        category = 'MISSING'
    elif state == 'PARKING_PRESENT':
        gross, building_area = s.number(raw.get('總價元')), s.number(raw.get('建物移轉總面積平方公尺'))
        if (counts[2] > 0 and len(details.get('park', [])) == counts[2]
                and item.get('details_complete') is True and item.get('main_key_unique') is True
                and price > 0 and area > 0 and gross is not None and gross > price
                and building_area is not None and building_area > area):
            category = 'PARKING_SEPARABLE_REPORTED'
        elif counts[2] > 0 and (price == 0 or area == 0):
            category = 'STRUCTURALLY_INSEPARABLE'
        else:
            category = 'AMBIGUOUS'
    else:
        category = 'AMBIGUOUS'
    return {'category': category, 'target_b_allowed': category == 'NO_PARKING_INCLUDED',
            'source_state': state, 'deduction_performed': False}


def month_profile(months: dict[str, int]) -> dict:
    keys = sorted(k for k, count in months.items() if count > 0)
    numbers = {chronology._month_number(k): k for k in keys}
    longest = []; run = []
    for number, month in sorted(numbers.items()):
        if run and number != chronology._month_number(run[-1]) + 1:
            run = []
        run.append(month)
        if len(run) > len(longest):
            longest = list(run)
    missing = []
    if numbers:
        missing = [f'{n//12:04d}-{n%12+1:02d}' for n in range(min(numbers), max(numbers)+1) if n not in numbers]
    total = sum(months.get(k, 0) for k in keys)
    return {'monthly_counts': {k: months[k] for k in keys}, 'unique_months': len(keys),
            'first_month': keys[0] if keys else None, 'last_month': keys[-1] if keys else None,
            'longest_contiguous_months': len(longest),
            'longest_contiguous_period': [longest[0], longest[-1]] if longest else [],
            'missing_months': missing, 'maximum_month_share': str(max(months[k] for k in keys)/total) if total else None}


def namespace_analysis(items: list[dict]) -> dict:
    families = defaultdict(list)
    occurrences = Counter()
    missing = 0
    for x in items:
        ids = l.identify(x)
        occurrences[ids['occurrence_id']] += 1
        if ids['transaction_family_id'] is None:
            missing += 1
        else:
            families[ids['transaction_family_id']].append(x)
    repeated = [xs for xs in families.values() if len(xs) > 1]
    conflicts = sum(len({l.identify(x)['version_id'] for x in xs}) > 1 for xs in repeated)
    cross_release = sum(len({x['release_id'] for x in xs}) > 1 for xs in repeated)
    candidate_fields = {}
    for label, field in (('main_serial', '編號'), ('transfer_number', '移轉編號')):
        keys = defaultdict(list); absent = 0
        for x in items:
            value = s.text(x.get('raw', {}).get(field))
            if not value:
                absent += 1
            else:
                scoped = l.digest([x.get('source_dataset_id'), s.source_county(x.get('member_name', '')), value])
                keys[scoped].append(x)
        repeated_keys = [xs for xs in keys.values() if len(xs) > 1]
        candidate_fields[label] = {
            'source_field': field,
            'nonblank_observations': len(items)-absent, 'missing_observations': absent,
            'unique_nonblank_scoped_keys': len(keys), 'repeated_key_groups': len(repeated_keys),
            'repeated_key_excess': sum(len(xs)-1 for xs in repeated_keys),
            'cross_release_repeated_groups': sum(len({x['release_id'] for x in xs}) > 1 for xs in repeated_keys),
            'different_main_serial_groups': sum(len({s.text(x['raw'].get('編號')) for x in xs}) > 1 for xs in repeated_keys),
            'stability_verdict': 'UNVERIFIED: no authoritative reuse/revision/replacement contract recovered',
            'privacy': 'Values remain private; only scoped aggregate key counts emitted.'}
    return {'verdict': 'UNVERIFIED_STABLE_NAMESPACE', 'identifier_kind': 'derived_research_identifier',
            'basis': 'SHA256(version,dataset,source county,reported official serial); no address/name inputs',
            'observations': len(items), 'missing_namespace_observations': missing, 'unique_derived_families': len(families),
            'repeated_family_groups': len(repeated), 'repeated_family_excess': sum(len(xs)-1 for xs in repeated),
            'conflicting_payload_groups': conflicts, 'cross_release_repeated_groups': cross_release,
            'duplicate_occurrence_locators': sum(v-1 for v in occurrences.values()),
            'observed_ambiguous_group_rate': str(len(repeated)/len(families)) if families else None,
            'cryptographic_collision_rate': 'NOT_IDENTIFIABLE_FROM_PROVISIONAL_KEY_REPETITION',
            'stable_namespace_attested_observations': 0,
            'candidate_fields': candidate_fields,
            'release_scoped_locator': 'archive/member/physical CSV record; unique occurrence, not stable transaction',
            'attribute_fingerprint': 'REJECTED: mutable prices/areas and identical visible attributes do not identify transactions',
            'privacy': 'No source identifiers or row-level hashes in committed aggregates.'}


def data_gate(items: list[dict], cutoff: str, *, history_certificate: dict | None,
              coverage_evidence: dict | None) -> dict:
    occurrence_ids = [l.identify(x)['occurrence_id'] for x in items]
    if len(set(occurrence_ids)) != len(occurrence_ids):
        raise ValueError('duplicate_physical_occurrence_input')
    selection = select_as_of(items, cutoff, history_certificate=history_certificate)
    normalized = [{**x, 'source_release_available_at': publication(x).get('available_at')
                   or x.get('source_release_available_at')} for x in items]
    evaluations = {l.identify(x)['occurrence_id']: b.classify(x, cutoff) for x in normalized}
    candidates = [x for x in normalized if evaluations[l.identify(x)['occurrence_id']]['target_valid']]
    pit = [x for x in selection['selected'] if b.classify(x, cutoff)['target_valid']
           and parking_treatment(x)['target_b_allowed']]
    # Existing maturity/frozen-ledger conditions remain mandatory. The callback
    # requalifies the full history at each freeze; a final-cutoff certificate is
    # never silently reused to prove an earlier fold.
    def cohort_selector(xs, freeze):
        frozen = select_as_of(xs, freeze, history_certificate=history_certificate)
        return {'selected_rows': [x for x in frozen['selected'] if b.classify(x, freeze)['target_valid']]}
    splits = chronology.design_splits(chronology.split_rows_from_items(pit), coverage_evidence=coverage_evidence,
                                     ledger_items=items, label_observation_cutoff=cutoff,
                                     cohort_selector=cohort_selector)
    certificate_ok = selection['history_certificate_valid']
    historical = [x for x in candidates if t.available_by(publication(x), cutoff)]
    parking = [x for x in candidates if parking_treatment(x)['target_b_allowed']]
    lineage = [x for x in candidates if certificate_ok and l.lineage_valid(x)]
    approved = pit if splits['viable'] and pit else []
    strict_visible = [x for x in normalized if t.available_by(publication(x), cutoff)]
    strict_a = strict_cohort.build_cohort(strict_visible, cutoff)
    strict_diagnostic = strict_cohort.build_cohort(normalized, cutoff)
    # Strict A still requires existing rights/unit gates plus this history proof.
    a_ids = {l.identify(x)['occurrence_id'] for x in strict_a['selected_rows']}
    a_pit = [x for x in pit if l.identify(x)['occurrence_id'] in a_ids]
    a_approved = a_pit if approved and len(a_pit) == len(pit) else []
    counts = {'raw_observations': len(items),
              'structurally_valid': sum(v['structurally_valid'] for v in evaluations.values()),
              'target_valid': len(candidates), 'historically_supported': len(historical),
              'lineage_valid': len(lineage), 'namespace_valid': len(candidates) if certificate_ok else 0,
              'parking_valid': len(parking), 'PIT_valid': len(pit), 'approved_training': len(approved)}
    groups = [('structurally_valid', [x for x in items if evaluations[l.identify(x)['occurrence_id']]['structurally_valid']], 'INVALID_STRUCTURE'),
              ('target_valid', candidates, 'TARGET_B_CONTRACT_EXCLUSION'),
              ('parking_valid', parking, 'NO_PARKING_NOT_CONFIRMED'),
              ('historically_supported', historical, 'EXACT_BYTE_HISTORICAL_AVAILABILITY_UNPROVEN'),
              ('namespace_valid', candidates if certificate_ok else [], 'STABLE_NAMESPACE_UNPROVEN'),
              ('lineage_valid', lineage, 'COMPLETE_REVISION_CANCELLATION_HISTORY_UNPROVEN'),
              ('PIT_valid', pit, 'ASOF_VERSION_EXCLUDED'),
              ('approved_training', approved, 'CHRONOLOGICAL_FOLDS_UNPROVEN')]
    active = {l.identify(x)['occurrence_id'] for x in items}; waterfall = []
    for stage, xs, reason in groups:
        remaining = active & {l.identify(x)['occurrence_id'] for x in xs}
        waterfall.append({'stage': stage, 'input_count': len(active), 'accepted_count': len(remaining),
                          'excluded_count': len(active-remaining), 'reason_counts': {reason: len(active-remaining)} if active-remaining else {}})
        active = remaining
    target_funnel = []
    active = set(evaluations)
    for stage in b.STAGES:
        rejected = {key for key in active if evaluations[key]['stage_reasons'][stage]}
        reason_counts = Counter(evaluations[key]['stage_reasons'][stage][0] for key in rejected)
        target_funnel.append({'stage': stage, 'input_count': len(active), 'accepted_count': len(active-rejected),
                              'excluded_count': len(rejected), 'reason_counts': dict(sorted(reason_counts.items()))})
        active -= rejected
    return {'version': GATE_VERSION, 'target_a': 'PASS' if a_approved else 'BLOCKED',
            'target_b': 'PASS' if approved else 'BLOCKED', 'ml_b_may_begin': bool(approved),
            'counts': counts, 'counts_semantics': 'Marginal diagnostics within target candidates; waterfall is sequential.',
            'waterfall': waterfall, 'asof_exclusions': selection['excluded_reasons'],
            'chronology': splits, 'target_a_pit_count': len(a_pit), 'target_a_approved': len(a_approved),
            'target_contract_waterfall': target_funnel,
            'target_a_existing_funnel': strict_diagnostic['funnel'],
            'baseline_contracts_prepared_this_lane': False,
            'baseline_contracts_ready_to_prepare': bool(approved),
            'production_valuation_approval': False}
