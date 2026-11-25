"""Validate the 2024 NY SPARCS Medicaid-primary public discharge extract."""
import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

import duckdb

from clean_hhs_providers import quote, rows

SOURCE_SHA = 'c9616fc90246d640620c176fbde02884bb6bffa95564a0dccccdc3b6b2b5e594'
COLUMNS = '''health_service_area hospital_county operating_certificate_number permanent_facility_id facility_name age_group zip_code gender race ethnicity length_of_stay type_of_admission patient_disposition discharge_year ccsr_diagnosis_code ccsr_diagnosis_description ccsr_procedure_code ccsr_procedure_description apr_drg_code apr_drg_description apr_mdc_code apr_mdc_description apr_severity_of_illness_code apr_severity_of_illness apr_risk_of_mortality apr_medical_surgical payment_typology_1 payment_typology_2 payment_typology_3 birth_weight emergency_department_indicator total_charges total_costs'''.split()
NULLABLE = set('health_service_area hospital_county operating_certificate_number permanent_facility_id zip_code ccsr_procedure_code ccsr_procedure_description payment_typology_2 payment_typology_3 birth_weight'.split())
PATTERNS = {'permanent_facility_id': '[0-9]{6}', 'operating_certificate_number': '[0-9]{7,8}',
            'zip_code': '[0-9]{3}|OOS', 'ccsr_diagnosis_code': '[A-Z]{3}[0-9]{3}',
            'ccsr_procedure_code': '[A-Z]{3}[0-9]{3}', 'apr_drg_code': '[0-9]{3}',
            'apr_mdc_code': '[0-9]{2}', 'length_of_stay': '[1-9]|[1-9][0-9]|1[01][0-9]|120\\+',
            'birth_weight': '[0-9]+|UNKN', 'total_charges': '([0-9]+(\\.[0-9]{1,2})?|\\.[0-9]{1,2})',
            'total_costs': '([0-9]+(\\.[0-9]{1,2})?|\\.[0-9]{1,2})'}


def checksum(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def clean(con, source):
    con.execute(f"CREATE OR REPLACE VIEW raw AS SELECT * FROM read_csv({quote(source)},all_varchar=true,header=true)")
    if con.table('raw').columns != COLUMNS:
        raise ValueError('Unexpected SPARCS schema')
    predicates = {f'missing_{c}': f'{c} IS NULL' for c in COLUMNS if c not in NULLABLE}
    predicates.update({f'format_{c}': f"{c} IS NOT NULL AND NOT regexp_full_match({c},{quote(p)})" for c,p in PATTERNS.items()})
    predicates.update({'payer': "payment_typology_1 <> 'Medicaid'", 'year': "discharge_year <> '2024'",
        'age': "age_group NOT IN ('0-17','18-29','30-49','50-69','70 or Older')", 'ed': "emergency_department_indicator NOT IN ('Y','N')",
        'severity': "NOT coalesce(apr_severity_of_illness_code=CASE apr_severity_of_illness WHEN 'Undetermined' THEN '0' WHEN 'Minor' THEN '1' WHEN 'Moderate' THEN '2' WHEN 'Major' THEN '3' WHEN 'Extreme' THEN '4' END,false)",
        'procedure_pair': '(ccsr_procedure_code IS NULL) <> (ccsr_procedure_description IS NULL)',
        'birth_weight_age': "birth_weight IS NOT NULL AND age_group<>'0-17'",
        'charge_cast': 'try_cast(total_charges AS DECIMAL(18,2)) IS NULL', 'cost_cast': 'try_cast(total_costs AS DECIMAL(18,2)) IS NULL',
        'redacted_geography': "(facility_name='Redacted for Confidentiality') <> (hospital_county IS NULL AND permanent_facility_id IS NULL AND operating_certificate_number IS NULL AND health_service_area IS NULL)"})
    counts = rows(con,'SELECT '+','.join(f'count(*) FILTER (WHERE {condition}) AS {label}' for label,condition in predicates.items())+' FROM raw')[0]
    if any(counts.values()):
        raise ValueError(f'SPARCS validation failures: { {k:v for k,v in counts.items() if v} }')
    con.execute("""CREATE OR REPLACE VIEW silver AS SELECT * REPLACE (
        CAST(discharge_year AS SMALLINT) AS discharge_year,
        CAST(apr_severity_of_illness_code AS SMALLINT) AS apr_severity_of_illness_code,
        CAST(total_charges AS DECIMAL(18,2)) AS total_charges,
        CAST(total_costs AS DECIMAL(18,2)) AS total_costs),
        'NY' AS hospital_state,
        CASE WHEN age_group='0-17' THEN 'pediatric' ELSE 'adult' END AS age_cohort,
        CASE WHEN length_of_stay='120+' THEN NULL ELSE CAST(length_of_stay AS SMALLINT) END AS stay_days_exact,
        CASE WHEN length_of_stay='120+' THEN 120 ELSE CAST(length_of_stay AS SMALLINT) END AS stay_days_lower_bound,
        length_of_stay='120+' AS stay_right_censored,
        CASE WHEN birth_weight='UNKN' THEN NULL ELSE try_cast(birth_weight AS INTEGER) END AS birth_weight_grams,
        CASE WHEN birth_weight='UNKN' THEN 'unknown' WHEN birth_weight IS NULL THEN 'not_reported' ELSE 'reported' END AS birth_weight_status,
        CASE WHEN zip_code IS NULL THEN 'not_reported_or_suppressed' WHEN zip_code='OOS' THEN 'out_of_state' ELSE 'prefix_reported' END AS residence_zip_status,
        facility_name='Redacted for Confidentiality' AS facility_redacted,
        emergency_department_indicator='Y' AS ed_indicator,
        CAST(total_costs AS DECIMAL(18,2))>CAST(total_charges AS DECIMAL(18,2)) AS cost_exceeds_charge,
        CAST(total_costs AS DECIMAL(18,2))=0 AS zero_estimated_cost,
        CAST(total_costs AS DECIMAL(18,2))>=1000000 AS high_estimated_cost_review
        FROM raw""")
    return counts


def run(source, output, report_path):
    if checksum(source)!=SOURCE_SHA:
        raise ValueError('SPARCS source hash differs from acquisition snapshot')
    output.mkdir(parents=True,exist_ok=True)
    parquet=output/'sparcs_ny_2024_medicaid_clean.parquet'
    summary=output/'sparcs_ny_2024_medicaid_cohort_summary.csv'
    with duckdb.connect(config={'threads':4,'memory_limit':'4GB'}) as con:
        failures=clean(con,source)
        input_count=con.table('raw').count('*').fetchone()[0]
        if input_count!=635606:
            raise ValueError('Unexpected acquired cohort size')
        missing=rows(con,'SELECT '+','.join(f'count(*) FILTER (WHERE {c} IS NULL) AS {c}' for c in COLUMNS)+' FROM raw')[0]
        exact_repeats=con.sql('SELECT count(*)-count(DISTINCT row('+','.join(COLUMNS)+')) FROM raw').fetchone()[0]
        con.execute(f"COPY (SELECT * FROM silver) TO {quote(parquet)} (FORMAT PARQUET, COMPRESSION ZSTD)")
        con.execute(f"CREATE VIEW result AS SELECT * FROM read_parquet({quote(parquet)})")
        # Check full output equality as multisets: duplicates are legitimate possible discharges.
        mismatch=con.sql('SELECT count(*) FROM (SELECT * FROM silver EXCEPT ALL SELECT * FROM result)').fetchone()[0]
        if mismatch or con.table('result').count('*').fetchone()[0]!=input_count:
            raise ValueError('Parquet roundtrip mismatch')
        stats=rows(con,"""SELECT count(*) AS rows,count(*) FILTER (WHERE stay_right_censored) AS censored_stays,
            count(*) FILTER (WHERE facility_redacted) AS redacted_facilities,count(*) FILTER (WHERE ed_indicator) AS ed_indicator_rows,
            count(*) FILTER (WHERE cost_exceeds_charge) AS cost_exceeds_charge,count(*) FILTER (WHERE zero_estimated_cost) AS zero_estimated_cost,
            count(*) FILTER (WHERE total_charges=0) AS zero_charges,count(*) FILTER (WHERE birth_weight_status='unknown') AS unknown_birth_weight,
            count(*) FILTER (WHERE high_estimated_cost_review) AS high_estimated_cost_review,
            min(total_costs) AS min_cost,max(total_costs) AS max_cost,min(total_charges) AS min_charge,max(total_charges) AS max_charge,
            quantile_cont(total_costs,0.99) AS estimated_cost_p99,sum(total_costs) AS total_estimated_cost,sum(total_charges) AS total_charges
            FROM result""")[0]
        query="""SELECT age_cohort, count(*) AS discharge_records, count(*) FILTER (WHERE ed_indicator) AS ed_indicator_records,
            count(*) FILTER (WHERE stay_right_censored) AS censored_stays,
            sum(total_costs) AS estimated_hospital_cost_usd, sum(total_charges) AS hospital_charges_usd
            FROM result GROUP BY 1 ORDER BY 1"""
        cohorts=rows(con,query)
        con.execute(f"COPY ({query}) TO {quote(summary)} (HEADER,DELIMITER ',')")
        schema=dict(zip(con.table('result').columns,map(str,con.table('result').types)))
        report={'source':str(source),'source_sha256':SOURCE_SHA,'input_rows':input_count,'input_columns':len(COLUMNS),'output_columns':len(schema),
                'missing_by_source_field':missing,'validation_failure_counts':failures,'identical_source_rows_beyond_first':exact_repeats,
                'records_removed':0,'profile':stats,'cohort_summary':cohorts,'schema':schema,'parquet_multiset_roundtrip':'passed',
                'outputs':{str(p):checksum(p) for p in [parquet,summary]},'built_at_utc':datetime.now(timezone.utc).isoformat(),'validation':'passed'}
    report_path.parent.mkdir(parents=True,exist_ok=True)
    report_path.write_text(json.dumps(report,indent=2,default=str)+'\n')
    return report


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source',type=Path,default=Path('data/raw/sparcs/sparcs_2024_medicaid_primary.csv'))
    parser.add_argument('--output',type=Path,default=Path('data/silver'))
    parser.add_argument('--report',type=Path,default=Path('reports/sparcs_cleaning.json'))
    args=parser.parse_args()
    print(json.dumps(run(args.source,args.output,args.report),indent=2,default=str))
