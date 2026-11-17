"""Research prototype; synthetic data only. Run: python pipeline.py --download."""
import argparse
import hashlib
import io
import json
from pathlib import Path
import urllib.request
import zipfile

import numpy as np
import pandas as pd
from sklearn.dummy import DummyClassifier
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import average_precision_score, brier_score_loss, roc_auc_score
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

URL = 'https://synthetichealth.github.io/synthea-sample-data/downloads/synthea_sample_data_csv_apr2020.zip'
TABLES = ['patients.csv', 'encounters.csv', 'payer_transitions.csv', 'payers.csv']
FEATURES = ['age', 'ed_visits', 'inpatient_visits', 'ambulatory_visits', 'wellness_visits']
ROOT = Path(__file__).resolve().parent


def download(raw):
    raw.mkdir(parents=True, exist_ok=True)
    content = urllib.request.urlopen(URL, timeout=90).read()
    archive = zipfile.ZipFile(io.BytesIO(content))
    for name in TABLES:
        matches = [n for n in archive.namelist() if Path(n).name == name]
        if len(matches) != 1:
            raise ValueError(f'Expected one {name}')
        (raw / name).write_bytes(archive.read(matches[0]))
    return {'url': URL, 'sha256': hashlib.sha256(content).hexdigest()}


def continuous_coverage(spells, start, end):
    """Conservative whole-year interpretation: END_YEAR is exclusive.

    Sample has year-only coverage, not monthly eligibility. Never claim exact
    continuous enrollment; use this proxy only for this synthetic demonstration.
    """
    cursor = start
    for a, b in sorted(spells):
        a, b = pd.Timestamp(int(a), 1, 1), pd.Timestamp(int(b), 1, 1)
        if a > cursor:
            break
        if b > cursor:
            cursor = b
        if cursor >= end:
            return True
    return False


def build_cohort(raw, index):
    p = pd.read_csv(raw / 'patients.csv', usecols=['Id', 'BIRTHDATE', 'DEATHDATE', 'GENDER', 'RACE'])
    e = pd.read_csv(raw / 'encounters.csv', usecols=['Id', 'PATIENT', 'START', 'ENCOUNTERCLASS'])
    t = pd.read_csv(raw / 'payer_transitions.csv')
    payers = pd.read_csv(raw / 'payers.csv', usecols=['Id', 'NAME'])
    if p.Id.duplicated().any() or e.Id.duplicated().any():
        raise ValueError('Duplicate patient or encounter IDs')
    e['date'] = pd.to_datetime(e.START, utc=True).dt.tz_localize(None)
    index = pd.Timestamp(index)
    start, end = index - pd.Timedelta(days=365), index + pd.Timedelta(days=90)
    if e.date.max() < end:
        raise ValueError('Requested outcome window extends beyond dataset observation')
    medicaid = set(payers.loc[payers.NAME.str.casefold() == 'medicaid', 'Id'])
    t = t[t.PAYER.isin(medicaid)]
    spells = {k: list(zip(g.START_YEAR, g.END_YEAR)) for k, g in t.groupby('PATIENT')}
    visits = {k: g for k, g in e.groupby('PATIENT')}
    rows = []
    for person in p.itertuples():
        birth = pd.Timestamp(person.BIRTHDATE)
        age = index.year - birth.year - ((index.month, index.day) < (birth.month, birth.day))
        # Death before outcome end means incomplete follow-up; exclude, not label zero.
        death = pd.to_datetime(person.DEATHDATE)
        if not 0 <= age < 18 or (pd.notna(death) and death < end):
            continue
        # Restrict first-year-of-life observations to after birth.
        if birth > start or not continuous_coverage(spells.get(person.Id, []), start, end):
            continue
        v = visits.get(person.Id, e.iloc[:0])
        past = v[(v.date >= start) & (v.date < index)]
        future = v[(v.date >= index) & (v.date < end)]
        counts = past.ENCOUNTERCLASS.value_counts()
        wellness = int(counts.get('wellness', 0))
        rows.append(dict(patient_id=person.Id, index_date=str(index.date()), age=age,
            gender=person.GENDER, race=person.RACE,
            ed_visits=int(counts.get('emergency', 0)),
            inpatient_visits=int(counts.get('inpatient', 0)),
            ambulatory_visits=int(counts.get('ambulatory', 0)), wellness_visits=wellness,
            # Prototype only: this is not the official WCV-CH denominator/value set.
            well_care_gap_proxy=int(wellness == 0) if age >= 3 else None,
            ed_next_90d=int((future.ENCOUNTERCLASS == 'emergency').any())))
    return pd.DataFrame(rows)


def metrics(y, probability):
    k = max(1, int(np.ceil(len(y) * .1)))
    ranked = np.argsort(-np.asarray(probability), kind='stable')[:k]
    positives = int(np.sum(y))
    return dict(n=len(y), events=positives, prevalence=float(np.mean(y)),
        roc_auc=float(roc_auc_score(y, probability)) if len(set(y)) == 2 else None,
        average_precision=float(average_precision_score(y, probability)) if positives else None,
        brier=float(brier_score_loss(y, probability)), outreach_capacity=k,
        precision_at_10pct=float(np.mean(np.asarray(y)[ranked])),
        recall_at_10pct=float(np.sum(np.asarray(y)[ranked]) / positives) if positives else None,
        mean_predicted_risk=float(np.mean(probability)))


def run(raw, reports):
    reports.mkdir(parents=True, exist_ok=True)
    # Disjoint members AND later dates for validation/test; one row/member/split.
    cohorts = []
    for date, split, lo, hi in [('2017-01-01', 'train', 0, 60), ('2018-01-01', 'validation', 60, 80), ('2019-01-01', 'test', 80, 100)]:
        c = build_cohort(raw, date)
        if c.empty:
            continue
        bucket = c.patient_id.map(lambda v: int(hashlib.sha256(v.encode()).hexdigest(), 16) % 100)
        c = c[(bucket >= lo) & (bucket < hi)].copy()
        c['split'] = split
        cohorts.append(c)
    if not cohorts:
        raise ValueError('No eligible children')
    cohort = pd.concat(cohorts, ignore_index=True)
    summary = {'data_type': 'public Synthea synthetic sample; not real Medicaid claims',
        'cohort_counts': cohort.groupby('split').size().to_dict(),
        'gap_proxy': {'eligible_age_3_17': int(cohort.well_care_gap_proxy.notna().sum()),
                      'missing_wellness_record': int(cohort.well_care_gap_proxy.sum())},
        'models': {}, 'limitations': ['Small synthetic sample; no clinical validity or impact established.',
            'Year-only enrollment proxy; children under 1 excluded for full history.',
            'No real claims adjudication lag modeled; encounters used as claims proxy.',
            'No model selection on test; all model comparisons are exploratory.']}
    train = cohort[cohort.split == 'train']
    test = cohort[cohort.split == 'test']
    if len(train) < 30 or train.ed_next_90d.value_counts().min() < 5 or train.ed_next_90d.nunique() < 2 or len(test) < 10:
        summary['status'] = 'insufficient_data_for_training'
    else:
        summary['status'] = 'synthetic_prototype_trained'
        models = {'prevalence_baseline': DummyClassifier(strategy='prior'),
            'logistic_regression': make_pipeline(StandardScaler(), LogisticRegression(C=1, max_iter=1000, random_state=42)),
            'gradient_boosting': HistGradientBoostingClassifier(max_iter=100, max_leaf_nodes=7, min_samples_leaf=10, random_state=42)}
        for name, model in models.items():
            model.fit(train[FEATURES], train.ed_next_90d)
            summary['models'][name] = {}
            for split in ['validation', 'test']:
                part = cohort[cohort.split == split]
                if part.empty:
                    continue
                prob = model.predict_proba(part[FEATURES])[:, 1]
                result = metrics(part.ed_next_90d.to_numpy(), prob)
                result['age_groups'] = {}
                for label, low, high in [('1-5', 1, 5), ('6-11', 6, 11), ('12-17', 12, 17)]:
                    mask = part.age.between(low, high).to_numpy()
                    if mask.sum() >= 10 and part.loc[mask, 'ed_next_90d'].sum() >= 3:
                        result['age_groups'][label] = metrics(part.loc[mask, 'ed_next_90d'].to_numpy(), prob[mask])
                    else:
                        result['age_groups'][label] = {'status': 'too_small_to_interpret'}
                summary['models'][name][split] = result
    # Publish summary only. Patient-level tables remain local and ignored.
    (reports / 'evaluation.json').write_text(json.dumps(summary, indent=2, allow_nan=False) + '\n')
    print(json.dumps(summary, indent=2, allow_nan=False))
    return summary


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--download', action='store_true')
    parser.add_argument('--raw', type=Path, default=ROOT / 'data/raw')
    parser.add_argument('--reports', type=Path, default=ROOT / 'reports')
    args = parser.parse_args()
    if args.download:
        provenance = download(args.raw)
        args.reports.mkdir(parents=True, exist_ok=True)
        (args.reports / 'data_provenance.json').write_text(json.dumps(provenance, indent=2) + '\n')
    run(args.raw, args.reports)
