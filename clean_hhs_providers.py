"""Profile HHS claims aggregates and construct conservative provider-state proxies."""
import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

import duckdb

from acquire_context_data import PROVIDER_SHA
from acquire_spending_data import HHS, checksum

STATES = "('NY','NJ','MD','VA','PA')"
START = "DATE '2018-01-01'"
END = "DATE '2024-12-31'"
SOURCES = {
    'hcpcs': ('medicaid-provider-spending.parquet', 'SERVICING_PROVIDER_NPI_NUM', 'HCPCS_CODE', 'TOTAL_PATIENTS'),
    'ndc': ('medicaid-provider-spending-ndc.parquet', 'PRESCRIBING_PROVIDER_NPI_NUM', 'NATIONAL_DRUG_CODE', 'TOTAL_UNIQUE_BENEFICIARIES'),
}


def quote(value):
    return "'" + str(value).replace("'", "''") + "'"


def macros(con):
    # NPI Luhn check digit, including the required 80840 prefix (sum 24).
    digit = [f"try_cast(substr(n,{i},1) AS INTEGER)" for i in range(1, 11)]
    terms = [f"({d}*2 - CASE WHEN {d}>=5 THEN 9 ELSE 0 END)" if i % 2 == 0 else d for i, d in enumerate(digit)]
    con.execute(f"CREATE MACRO valid_npi(n) AS coalesce(regexp_full_match(n,'[0-9]{{10}}') AND (24+{'+'.join(terms)})%10=0,false)")
    repeated = '|'.join(str(i)*11 for i in range(10))
    con.execute(f"CREATE MACRO valid_ndc(n) AS coalesce(regexp_full_match(n,'[0-9]{{11}}') AND NOT regexp_full_match(n,'{repeated}'),false)")
    con.execute("CREATE MACRO valid_hcpcs(n) AS coalesce(regexp_full_match(n,'[0-9]{5}|[A-Z][0-9]{4}|[0-9]{4}[A-Z]'),false)")


def export(con, query, path):
    con.execute(f"COPY ({query}) TO {quote(path)} (FORMAT PARQUET, COMPRESSION ZSTD)")
    return con.read_parquet(str(path)).count('*').fetchone()[0]


def rows(con, query):
    result = con.execute(query)
    names = [c[0] for c in result.description]
    return [dict(zip(names, line)) for line in result.fetchall()]


def enrollment(con, source, out):
    con.execute(f"CREATE VIEW enrollment_raw AS SELECT * FROM read_parquet({quote(source)})")
    con.execute(f"""CREATE VIEW enrollment_flags AS SELECT *, valid_npi(NPI) AS npi_valid,
        ENRL_END_DT IS NULL AS open_end_assumed,
        coalesce(ENRL_END_DT >= ENRL_START_DT, ENRL_END_DT IS NULL AND ENRL_START_DT IS NOT NULL)
        AND ENRL_START_DT IS NOT NULL AS interval_valid,
        ENRL_STATUS_CD IN ('02','03','05') AND ENRL_PLAN_CD='1' AS active_medicaid_evidence
        FROM enrollment_raw""")
    path = out / 'hhs_provider_enrollment_clean.parquet'
    n = export(con, f'SELECT * FROM enrollment_flags WHERE STATE_CD IN {STATES}', path)
    profile = rows(con, f"""SELECT STATE_CD AS state,count(*) AS records,count(*) FILTER (WHERE NOT npi_valid) AS invalid_npi,
        count(*) FILTER (WHERE NOT interval_valid) AS invalid_interval,count(*) FILTER (WHERE open_end_assumed) AS open_end,
        count(*) FILTER (WHERE active_medicaid_evidence) AS active_medicaid_records
        FROM enrollment_flags WHERE STATE_CD IN {STATES} GROUP BY 1 ORDER BY 1""")
    if sum(x['records'] for x in profile) != n or len(profile) != 5:
        raise ValueError('Enrollment coverage/count mismatch')
    # All national states participate in ambiguity detection, including non-active and CHIP segments.
    con.execute(f"CREATE TABLE candidates AS SELECT DISTINCT NPI FROM enrollment_flags WHERE STATE_CD IN {STATES} AND npi_valid")
    con.execute(f"""CREATE TABLE intervals AS SELECT DISTINCT e.NPI,STATE_CD,
        date_diff('month',{START},greatest(ENRL_START_DT,{START})) AS first_month,
        date_diff('month',{START},least(coalesce(ENRL_END_DT,{END}),{END})) AS last_month,
        active_medicaid_evidence,open_end_assumed
        FROM enrollment_flags e SEMI JOIN candidates c USING(NPI)
        WHERE interval_valid AND ENRL_START_DT<={END} AND coalesce(ENRL_END_DT,{END})>={START}""")
    # Compact 84-bit interval masks avoid exploding long segments into billions of intermediate rows.
    con.execute("""CREATE TABLE state_masks AS WITH masks AS (
        SELECT *, ((1::HUGEINT << (last_month+1)) - (1::HUGEINT << first_month)) AS mask FROM intervals)
        SELECT NPI,STATE_CD,bit_or(mask) AS month_mask,
        bit_or(CASE WHEN active_medicaid_evidence THEN mask ELSE 0::HUGEINT END) AS active_mask,
        bit_or(CASE WHEN open_end_assumed THEN mask ELSE 0::HUGEINT END) AS open_mask
        FROM masks GROUP BY 1,2""")
    con.execute("DROP TABLE intervals")
    con.execute("""CREATE TABLE provider_map AS SELECT NPI,list(struct_pack(state:=STATE_CD, months:=month_mask,
        active:=active_mask, open_end:=open_mask)) AS states FROM state_masks GROUP BY NPI""")
    summary = rows(con, """SELECT count(*) AS candidate_providers,
        count(*) FILTER (WHERE len(states)>1) AS providers_with_multiple_states_over_period FROM provider_map""")[0]
    summary['distinct_provider_state_pairs'] = con.table('state_masks').count('*').fetchone()[0]
    con.execute('DROP TABLE state_masks')
    # One row per candidate NPI; list filtering by month does not fan out spending rows.
    con.execute("""CREATE MACRO month_evidence(states,idx) AS list_filter(states,lambda s: (s.months & (1::HUGEINT << idx))<>0)""")
    return path, {'national_rows': con.table('enrollment_raw').count('*').fetchone()[0], 'five_state_rows': n, 'state_profile': profile, 'monthly_linkage': summary}


def spending(con, kind, source, out):
    _, other, code, beneficiaries = SOURCES[kind]
    # The source stays intact. No beneficiary-level reconstruction or summation of unique counts.
    con.execute(f"""CREATE OR REPLACE VIEW spending_flags AS SELECT *,
        try_strptime(CLAIM_FROM_MONTH,'%Y-%m')::DATE AS claim_month,
        CASE WHEN BILLING_PROVIDER_NPI_NUM IS NULL THEN 'missing' WHEN valid_npi(BILLING_PROVIDER_NPI_NUM) THEN 'valid_checksum' ELSE 'invalid' END AS billing_status,
        CASE WHEN {other} IS NULL THEN 'missing' WHEN valid_npi({other}) THEN 'valid_checksum' ELSE 'invalid' END AS other_status,
        valid_{kind}({code}) AS code_format_ok,
        coalesce({beneficiaries}>=12 AND TOTAL_CLAIM_LINES>=12 AND {beneficiaries}<=TOTAL_CLAIM_LINES,false) AS counts_ok,
        coalesce(isfinite(TOTAL_PAID),false) AS paid_ok,
        coalesce(abs(TOTAL_PAID)>=1000000000,false) AS extreme_paid
        FROM read_parquet({quote(source)})""")
    con.execute(f"""CREATE OR REPLACE VIEW linked AS WITH evidence AS (
        SELECT s.*, date_diff('month',{START},claim_month) AS idx,
        CASE WHEN claim_month BETWEEN {START} AND {END} THEN month_evidence(p.states,date_diff('month',{START},claim_month)) END AS matches
        FROM spending_flags s LEFT JOIN provider_map p ON s.BILLING_PROVIDER_NPI_NUM=p.NPI),
        resolved AS (SELECT *, coalesce(len(matches),0) AS state_count, matches[1].state AS unique_state,
        coalesce((matches[1].active & (1::HUGEINT << CASE WHEN idx BETWEEN 0 AND 83 THEN idx END))<>0,false) AS active_medicaid_evidence,
        coalesce(len(list_filter(matches,lambda s: (s.open_end & (1::HUGEINT << CASE WHEN idx BETWEEN 0 AND 83 THEN idx END))<>0))>0,false) AS assumed_end FROM evidence)
        SELECT *,
        CASE WHEN billing_status <> 'valid_checksum' THEN billing_status || '_billing'
             WHEN state_count=0 THEN 'no_candidate_month'
             WHEN state_count>1 THEN 'multiple_states'
             WHEN unique_state NOT IN {STATES} THEN 'unique_outside_scope'
             WHEN NOT active_medicaid_evidence THEN 'no_active_medicaid_evidence'
             ELSE 'unique_in_scope_provider_proxy' END AS link_status,
        CASE WHEN state_count=1 AND unique_state IN {STATES} AND active_medicaid_evidence AND billing_status='valid_checksum' THEN unique_state END AS provider_state_proxy,
        assumed_end AS open_end_assumed FROM resolved""")
    # Group once with all flags. Keep code detail only for the exploratory subset; do not merge HCPCS/NDC amounts.
    con.execute(f"""CREATE OR REPLACE TABLE grouped AS SELECT claim_month,link_status,provider_state_proxy,
        billing_status,other_status,code_format_ok,counts_ok,paid_ok,extreme_paid,open_end_assumed,
        CASE WHEN link_status='unique_in_scope_provider_proxy' AND code_format_ok AND counts_ok AND paid_ok AND NOT extreme_paid
                  AND claim_month BETWEEN {START} AND {END} THEN {code} END AS code,
        count(*) AS published_cells,sum(TOTAL_CLAIM_LINES) AS claim_lines,
        sum(CASE WHEN paid_ok THEN try_cast(round(TOTAL_PAID,2) AS DECIMAL(38,2)) END) AS source_paid_usd,
        count(*) FILTER (WHERE paid_ok AND TOTAL_PAID<0) AS negative_paid_cells,
        count(*) FILTER (WHERE paid_ok AND TOTAL_PAID=0) AS zero_paid_cells
        FROM linked GROUP BY ALL""")
    audit = out / f'hhs_{kind}_monthly_audit.parquet'
    proxy = out / f'hhs_{kind}_provider_state_code_month.parquet'
    measures = 'sum(published_cells)::BIGINT AS published_cells,sum(claim_lines)::BIGINT AS claim_lines,sum(source_paid_usd) AS source_paid_usd,sum(negative_paid_cells)::BIGINT AS negative_paid_cells,sum(zero_paid_cells)::BIGINT AS zero_paid_cells'
    n_audit = export(con, f'SELECT claim_month,link_status,provider_state_proxy,billing_status,other_status,code_format_ok,counts_ok,paid_ok,extreme_paid,open_end_assumed,{measures} FROM grouped GROUP BY ALL', audit)
    n_proxy = export(con, f'SELECT claim_month,provider_state_proxy,code,{measures} FROM grouped WHERE code IS NOT NULL GROUP BY ALL', proxy)
    raw_n = con.read_parquet(str(source)).count('*').fetchone()[0]
    stats = rows(con, """SELECT sum(published_cells)::BIGINT AS rows,
        sum(published_cells) FILTER (WHERE NOT code_format_ok)::BIGINT AS invalid_code_rows,
        coalesce(sum(published_cells) FILTER (WHERE NOT counts_ok),0)::BIGINT AS invalid_count_rows,
        coalesce(sum(published_cells) FILTER (WHERE NOT paid_ok),0)::BIGINT AS invalid_paid_rows,
        sum(published_cells) FILTER (WHERE extreme_paid)::BIGINT AS extreme_paid_rows,
        sum(published_cells) FILTER (WHERE code IS NOT NULL)::BIGINT AS proxy_cells,
        sum(negative_paid_cells)::BIGINT AS negative_paid_rows,sum(zero_paid_cells)::BIGINT AS zero_paid_rows,
        min(claim_month) AS first_month,max(claim_month) AS last_month,
        coalesce(sum(published_cells) FILTER (WHERE claim_month IS NULL OR claim_month<DATE '2018-01-01' OR claim_month>DATE '2024-12-31'),0)::BIGINT AS invalid_month_rows
        FROM grouped""")[0]
    if stats['rows'] != raw_n or stats['invalid_month_rows'] or stats['invalid_count_rows'] or stats['invalid_paid_rows']:
        raise ValueError(f'{kind}: unexpected row count/date/count/payment validation failure')
    proxy_check = con.read_parquet(str(proxy)).aggregate('sum(published_cells)').fetchone()[0]
    if proxy_check != stats['proxy_cells']:
        raise ValueError('Proxy rollup cell-count mismatch')
    stats.update({'audit_rows': n_audit,'proxy_rows': n_proxy,
        'link_rows': rows(con,'SELECT link_status,sum(published_cells)::BIGINT AS cells FROM grouped GROUP BY 1 ORDER BY 1'),
        'proxy_by_state': rows(con,'SELECT provider_state_proxy,sum(published_cells)::BIGINT AS cells FROM grouped WHERE code IS NOT NULL GROUP BY 1 ORDER BY 1')})
    con.execute('DROP TABLE grouped')
    return [audit,proxy],stats


def validate_artifacts(out, report):
    """Independently reconcile exported audit and proxy totals, and their grains."""
    with duckdb.connect() as con:
        for kind, stats in report['spending'].items():
            audit = f"read_parquet({quote(out/f'hhs_{kind}_monthly_audit.parquet')})"
            proxy = f"read_parquet({quote(out/f'hhs_{kind}_provider_state_code_month.parquet')})"
            condition = "link_status='unique_in_scope_provider_proxy' AND code_format_ok AND counts_ok AND paid_ok AND NOT extreme_paid"
            measures = 'sum(published_cells),sum(claim_lines),sum(source_paid_usd)'
            if con.sql(f'SELECT sum(published_cells) FROM {audit}').fetchone()[0] != stats['rows']:
                raise ValueError('Exported audit row-count mismatch')
            if con.sql(f'SELECT {measures} FROM {audit} WHERE {condition}').fetchone() != con.sql(f'SELECT {measures} FROM {proxy}').fetchone():
                raise ValueError('Exported proxy totals do not reconcile to eligible audit strata')
            if con.sql(f'SELECT count(*) FROM (SELECT claim_month,provider_state_proxy,code FROM {proxy} GROUP BY ALL HAVING count(*)>1)').fetchone()[0]:
                raise ValueError('Duplicate proxy output key')
            stats['export_reconciliation'] = 'passed'
            stats['billing_status_rows'] = rows(con,f'SELECT billing_status,sum(published_cells)::BIGINT AS cells FROM {audit} GROUP BY 1 ORDER BY 1')
            stats['other_status_rows'] = rows(con,f'SELECT other_status,sum(published_cells)::BIGINT AS cells FROM {audit} GROUP BY 1 ORDER BY 1')
            stats['eligible_open_end_cells'] = con.sql(f'SELECT sum(published_cells) FROM {audit} WHERE {condition} AND open_end_assumed').fetchone()[0]
            stats['diagnostic_paid_by_code_format'] = rows(con,f'SELECT code_format_ok,sum(published_cells)::BIGINT AS cells,sum(source_paid_usd) AS raw_cell_amount_usd FROM {audit} GROUP BY 1 ORDER BY 1')
            stats['invalid_count_rows'],stats['invalid_paid_rows'],stats['invalid_month_rows'] = con.sql(f"""SELECT
                coalesce(sum(published_cells) FILTER (WHERE NOT counts_ok),0),
                coalesce(sum(published_cells) FILTER (WHERE NOT paid_ok),0),
                coalesce(sum(published_cells) FILTER (WHERE claim_month IS NULL OR claim_month<DATE '2018-01-01' OR claim_month>DATE '2024-12-31'),0) FROM {audit}""").fetchone()
            if any(stats[k] for k in ['invalid_count_rows','invalid_paid_rows','invalid_month_rows']):
                raise ValueError('Exported audit contains invalid months, counts or paid amounts')
    return report


def run(root, out, report_path, work_db):
    out.mkdir(parents=True,exist_ok=True)
    sources = root / 'raw/hhs'
    expected = {name: digest for name, (_, _, digest) in HHS.items()}
    expected['medicaid-provider-enrollment-segments.parquet'] = PROVIDER_SHA
    for name, digest in expected.items():
        if checksum(sources/name) != digest:
            raise ValueError(f'Source checksum mismatch: {name}')
    with duckdb.connect(str(work_db),config={'threads':4,'memory_limit':'4GB','preserve_insertion_order':False,'temp_directory':str(root/'duckdb_spill'),'max_temp_directory_size':'8GB'}) as con:
        macros(con)
        path, er = enrollment(con,sources/'medicaid-provider-enrollment-segments.parquet',out)
        paths, report = [path], {'enrollment':er,'spending':{},'source_sha256':expected}
        for kind,(name,*_) in SOURCES.items():
            print(f'Processing {kind}',flush=True)
            new_paths, stats = spending(con,kind,sources/name,out)
            paths.extend(new_paths); report['spending'][kind]=stats
        report.update({'built_at_utc':datetime.now(timezone.utc).isoformat(),'outputs':{str(p):checksum(p) for p in paths},'validation':'passed'})
    validate_artifacts(out,report)
    report_path.parent.mkdir(parents=True,exist_ok=True)
    report_path.write_text(json.dumps(report,indent=2,default=str)+'\n')
    return report


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--data-dir',type=Path,default=Path('data'))
    parser.add_argument('--output',type=Path,default=Path('data/silver'))
    parser.add_argument('--report',type=Path,default=Path('reports/hhs_provider_cleaning.json'))
    args=parser.parse_args()
    # In-memory catalog with DuckDB automatic temporary spill; no persistent intermediate DB.
    print(json.dumps(run(args.data_dir,args.output,args.report,':memory:'),indent=2,default=str))
