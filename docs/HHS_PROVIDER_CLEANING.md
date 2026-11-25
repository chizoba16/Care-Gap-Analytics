# Lab 04 — HHS provider enrollment and spending

## Purpose and source boundaries

Work with the actual 2018–2024 national [HCPCS](https://opendata.hhs.gov/datasets/medicaid-provider-spending/), [NDC](https://opendata.hhs.gov/datasets/medicaid-provider-spending-ndc/) and [provider enrollment](https://opendata.hhs.gov/datasets/medicaid-provider-enrollment-segments/) releases, previously downloaded and checksummed. This lab produces a five-state enrollment Silver table, national spending audits and exploratory five-state provider-attributed code/month rollups. It does not create a complete state claims dataset, patient-level data or a verified drug/product catalog. New York, New Jersey, Maryland, Virginia and Pennsylvania are in scope. Age is unavailable; do not infer adult or child spending from the releases.

## Step 1 — Columnar profiling

```python
import duckdb
db = duckdb.connect()
path = 'data/raw/hhs/medicaid-provider-spending.parquet'
print(db.sql(f"DESCRIBE SELECT * FROM read_parquet('{path}')"))
print(db.sql(f"SELECT count(*) FROM read_parquet('{path}')"))
```

National row counts: 238,015,729 HCPCS cells; 21,515,000 NDC cells; 65,970,112 enrollment segments. The spending cells have billing NPI, servicing/prescribing NPI, code and claim month as the published grain. The claim date anchor can use the line end date. Counts are claim lines and cell-level unique beneficiaries, not distinct claims or persons across cells. Small cells are withheld by HHS. Never infer their values or fill absent cells with zero.

## Step 2 — Design validation flags

- NPIs remain strings. Apply 10-digit syntax and the Luhn check digit with the 80840 prefix to both provider roles. A successful checksum is not proof of identity, registry status or licensure. Missing and invalid identifiers are separate statuses.
- HCPCS screening accepts five-digit, letter-plus-four-digit, and four-digit-plus-letter formats. State-specific or other nonconforming codes are not automatically incorrect; place them in an audit category rather than deleting them from the source. No official code-set lookup is performed.
- NDC screening keeps 11-digit strings with leading zeros and excludes all-one-digit repeated fills. It is a format screen, not verification against FDA product history. HHS warns about placeholder NDCs dominating unfiltered paid amounts.
- Verify month range (Jan 2018–Dec 2024), both published counts at least 12 and beneficiaries no greater than lines, finite paid amounts. Retain negative and zero paid values. Mark absolute paid amounts of at least $1 billion per published cell as an exploratory review threshold; this is a project-specific heuristic, not a fraud rule. Exclude these from exploratory rollups only.
- Source paid amounts are double precision; round each cell to cents and aggregate as DECIMAL(38,2). Preserve raw files; no assertion that reported amounts equal reimbursed claims. The annual source 2024 release is preliminary. NDC can include denied claims and encounter lines; never combine HCPCS and NDC totals or add them to CMS-64.

## Step 3 — Clean enrollment and temporal linkage

Keep all five-state enrollment segments, source flags and dates. Add `npi_valid`, `interval_valid`, `open_end_assumed`, `active_medicaid_evidence`. Null end dates are assumed to extend to the end of the study window; clip all dates to Jan 2018–Dec 2024 when linking. Reject reversed intervals from linkage, not the stored source. Treat a segment as overlapping a month when any date overlaps inclusive bounds; the status may change within the month. The active Medicaid evidence rule is plan code 1 and status 02, 03 or 05; it is a conservative project filter, not a determination of payment eligibility. Other status/plan records still count as competing state evidence.

The key insight: using just the five-state extract to assign spending would miss a simultaneous enrollment in another state. Select distinct checksum-valid candidate NPIs found in the five-state enrollment records, then inspect **all national states** for those candidates. Group overlapping segments by NPI/state. Encode the 84 study months as a 128-bit integer: each bit represents a month, and a bitwise OR unifies overlapping intervals. This avoids expanding each long segment into many rows and overflowing memory/disk. One NPI has one list of state masks; filter the list to the claim month. The left join is cardinality-preserving at the source-cell level. Only a single overlapping state in scope with active Medicaid evidence qualifies as the exploratory billing-provider proxy. No fallback to servicing/prescribing NPI; that would change the meaning. Open-ended assumptions and ambiguous results remain visible in the audit. `no_candidate_month` combines NPIs outside the candidate universe and candidates with no overlap; it is not a national non-enrollment determination.

## Step 4 — Produce and validate outputs

```bash
python -m pip install -r requirements.txt
python clean_hhs_providers.py
python -m unittest discover -s tests -v
```

The pipeline uses DuckDB, four threads, a 4 GB memory budget and a bounded temporary spill directory under `data/`, an intentional departure from loading everything into pandas. It verifies all three published SHA-256 hashes. It produces:

| File (under `data/silver/`) | Grain |
|---|---|
| `hhs_provider_enrollment_clean.parquet` | Original five-state segment with flags; source duplicates preserved |
| `hhs_hcpcs_monthly_audit.parquet` / `hhs_ndc_monthly_audit.parquet` | National month × link/quality strata, including excluded cells |
| `hhs_hcpcs_provider_state_code_month.parquet` / `hhs_ndc_provider_state_code_month.parquet` | In-scope unique billing-provider state proxy × month × format-screened code |

`published_cells`, `claim_lines`, `source_paid_usd`, `negative_paid_cells` and `zero_paid_cells` are additive only within a single release and disjoint strata. No unique beneficiary counts are summed. The source paid amounts in the audit are diagnostic, not estimates of total state spending. The proxy rollups lose individual provider identity; later provider-level models require a more granular validated view. Open-end flags are retained in the audit (not the code rollups). Exact global source key uniqueness was not verified; no automatic deduplication or claim reconstruction has been attempted. Cell count reconciliation verifies the join did not multiply rows. See [validation report](../reports/hhs_provider_cleaning.json) for observed counts, checksums and results.

### Observed results (November 24, 2026, New York time)

| Metric | HCPCS | NDC |
|---|---:|---:|
| All national cells audited | 238,015,729 | 21,515,000 |
| Missing billing NPI | 7,806,309 | 580,607 |
| Invalid billing NPI (format/checksum) | 67,997 | 2,916 |
| Nonconforming code format / repeated fills | 607,098 | 1,163,224 |
| Absolute paid amount ≥ $1 billion | 62 | 21 |
| Competing state evidence in claim month | 117,335,790 | 16,548,762 |
| Cells passing exploratory proxy rules | 10,647,363 | 128,606 |
| Monthly code rollup rows | 401,433 | 39,238 |

All 3,648,557 five-state enrollment rows were retained; 261,142 had invalid NPI format/checksum, 2,137,051 had null end dates, no reversed intervals. The national candidate map contains 1,070,264 distinct candidate NPIs with overlapping study-period evidence, 589,219 of them associated with more than one state at some time in the study (not necessarily concurrently). No invalid months, counts or non-finite payments were found in either spending release. All exported audit and eligible proxy counts, paid amounts and claim lines reconcile; no duplicate proxy keys. All 20 repository unit tests passed.

**Major validity limitation:** eligible proxy cells constitute only 4.47% of national HCPCS cells and 0.60% of national NDC cells. 90.0% and 92.9%, respectively, of eligible cells have some overlapping open-end evidence; that is not necessarily the only qualifying segment. This is a highly selected, assumption-sensitive subset; neither representative five-state spending nor valid state-to-state performance rankings have been established. Treat these as exploratory technical artifacts and evaluate alternate linkage assumptions before using them in Gold or models.

| State | Enrollment segments | Eligible HCPCS cells | Eligible NDC cells |
|---|---:|---:|---:|
| NY | 323,566 | 5,140,541 | 1,763 |
| NJ | 221,172 | 1,613,519 | 18,784 |
| MD | 1,524,148 | 1,158,335 | 33,355 |
| VA | 683,652 | 1,744,994 | 58,036 |
| PA | 896,019 | 989,974 | 16,668 |

## Step 5 — Practice SQL

```sql
SELECT link_status, SUM(published_cells) AS cells
FROM read_parquet('data/silver/hhs_hcpcs_monthly_audit.parquet')
GROUP BY 1 ORDER BY 2 DESC;
```

```sql
SELECT provider_state_proxy, claim_month, code, claim_lines, source_paid_usd
FROM read_parquet('data/silver/hhs_ndc_provider_state_code_month.parquet')
ORDER BY claim_month, provider_state_proxy, code;
```

Exercises: compute the share of cells without a permissible link; compare audit amounts for valid versus nonconforming codes (diagnostic only); examine how open-ended assumption flags change the eligible cell counts; explain why multiple segments must be resolved before joining; investigate code reference validation and price per claim line, not per unique beneficiary. Never equate provider enrollment state to beneficiary residence, actual claim-submitting state, age, Medicaid-only payments, care gaps or inappropriate utilization. No model training or validated state expenditure estimate occurs here.
