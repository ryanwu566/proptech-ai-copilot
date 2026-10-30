"""Toy artifact metadata. These identities describe synthetic test data only."""
def metadata(version='test-v1'):
    from services.valuation_ml.admission import SPLITS, continuous_window, gate_decision
    from services.valuation_ml.training import library_versions
    return dict(model_version=version,dataset_fingerprint='a'*64,admitted_rows=90,
        admitted_window={'start':'2017-01-01','end':'2026-06-30','release_count':40,
                         'historical_publication_proven':False,'population_completeness_proven':False},
        split_definition=SPLITS,split_counts={'train':60,'validation':20,'holdout':10},
        fitted_through='2025-06-30',generated_at='2026-10-29T00:00:00Z',libraries=library_versions(),
        training_authorization=gate_decision(verified=True),
        prediction_date_min='2025-07-01',prediction_date_max='2026-12-27',
        support={'minimum_fit_rows':50,'minimum_recent_rows':20,'low_support_below':200,
                 'cells':{},'numeric_bounds':{}},
        evaluation={'overall':{'mae_ntd_ping':20000},'slices':{'geography':{}}},
        provenance={'source_artifact_hashes':{k:'b'*64 for k in
            ('coverage.json','lineage.sqlite','provenance-manifest.json','schema.json','transactions.jsonl.gz')},
            'source_transform_sha256':{'synthetic-source.py':'c'*64},
            'split_identity_sha256':{k:'d'*64 for k in SPLITS},
            'stage3_code_sha256':{'synthetic-test.py':'e'*64}},
        limitations=['Parking and whole-dwelling rights are unverified.',
                     'Retrospective snapshot evaluation; historical publication is unproven.',
                     'No calibrated confidence probability. Synthetic test fixture.'])
