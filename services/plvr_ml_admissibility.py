"""Bounded v1 evidence/claim policy, independent of frozen fitting features.

This does not grant ML-A/B, parking-exclusive or whole-dwelling authorization.
It distinguishes admissible archive observations from unproved legal/PIT claims.
"""
VERSION='plvr-bounded-transfer-evidence-v1'
KNOWN_SERIAL='RPWNMLNKNHLGFBF78EA'


def public_scope():
    return dict(evidence_contract_version=VERSION,requested_value_basis='reported_transfer',
        publication_evidence='bounded_archive_snapshot',historical_pit_supported=False,
        cancellation_handling='exclude_observed_conflicts_and_note_tainted_families',
        cancellation_event_ledger_available=False,
        current_cancellation_state_verified=False,unobserved_cancellation_risk='not_eliminated',
        parking_features_included=False,parking_exclusive_value_supported=False,
        rights_basis='reported_transfer_only_rights_unverified',whole_dwelling_value_supported=False,
        partial_rights_valuation_supported=False,
        total_price_basis='unit_estimate_times_reported_registered_transferred_area',
        whole_property_scaling_supported=False)


def family_admissibility(evidence):
    """Judge observed lineage; absence never proves cancellation or active state.

    Counts/note flags must come from the complete retained ledger, not a selected
    eligible version. A canceled/superseded/conflicting family has no fallback to
    an older apparently eligible row. Unknown unreported events remain unknown.
    """
    checks=(
        (evidence.get('official_serial')==KNOWN_SERIAL,'known_related_party_38652'),
        (evidence.get('explicit_cancelled') is True,'explicit_cancellation'),
        (evidence.get('explicit_superseded') is True,'explicit_supersession'),
        (evidence.get('identity_has_note') is not False,'observed_special_note'),
        (evidence.get('fact_has_note') is not False,'note_tainted_fact_family'),
        (type(evidence.get('version_count')) is not int or evidence['version_count']!=1,
            'observed_revision_conflict'),
        (type(evidence.get('fact_identity_count')) is not int or evidence['fact_identity_count']!=1,
            'ambiguous_identity'),
        (evidence.get('quality_reason') is not None,'invalid_source_observation'))
    reason=next((reason for failed,reason in checks if failed),None)
    return dict(evidence_contract_version=VERSION,admit_archive_observation=reason is None,reason=reason,
                historical_pit_proven=False,current_cancellation_state_proven=False)


def rights_eligibility(status,purpose):
    """A flag/land fraction is never whole-dwelling evidence in this capability."""
    if purpose!='reported_transfer':
        return dict(eligible=False,reason='unsupported_whole_or_share_valuation_claim')
    if status not in {'UNVERIFIED','RIGHTS_UNKNOWN','FULL_RIGHTS_CONFIRMED'}:
        return dict(eligible=False,reason='known_partial_or_unsupported_rights_scope')
    return dict(eligible=True,reason=None,whole_dwelling_verified=False,
                scope='reported_registered_transfer_only')
