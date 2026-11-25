"""Profile, clean, and validate the five-state CMS enrollment snapshot."""

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

import duckdb
import pandas as pd

from acquire_public_data import STATES

COUNTS = [
    "total_medicaid_enrollment",
    "total_chip_enrollment",
    "total_medicaid_and_chip_enrollment",
    "total_adult_medicaid_enrollment",
    "medicaid_and_chip_child_enrollment",
]
KEY = ["cga_state", "reporting_period"]
REQUIRED = KEY + ["state_abbreviation", "state_name", "final_report", "preliminary_or_updated"] + COUNTS


def digest(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def clean(raw):
    missing = set(REQUIRED) - set(raw.columns)
    if missing:
        raise ValueError(f"Missing required columns: {sorted(missing)}")
    if set(raw.cga_state) != set(STATES):
        raise ValueError("Unexpected state coverage")
    if not raw.cga_state.eq(raw.state_abbreviation).all() or not raw.cga_state.map(STATES).eq(raw.state_name).all():
        raise ValueError("State identifiers disagree")
    if not raw.reporting_period.str.fullmatch(r"\d{6}").all():
        raise ValueError("Invalid reporting period format")
    dates = pd.to_datetime(raw.reporting_period, format="%Y%m", errors="raise")
    if not raw.final_report.isin(["Y", "N"]).all() or not raw.preliminary_or_updated.isin(["P", "U"]).all():
        raise ValueError("Unexpected reporting flags")
    if raw.duplicated(KEY + ["final_report"]).any():
        raise ValueError("Duplicate state/month/report status; investigate before choosing a record")

    # Keep source rows intact. Only final reports enter the Silver table.
    final = raw.loc[raw.final_report.eq("Y")].copy()
    if set(final.cga_state) != set(STATES):
        raise ValueError("Final report coverage incomplete")
    preliminary = raw.loc[raw.final_report.eq("N")]
    matched = final.merge(preliminary, on=KEY, suffixes=("_final", "_preliminary"), validate="one_to_one")
    metric = "total_medicaid_and_chip_enrollment"
    both = matched[metric + "_final"].ne("") & matched[metric + "_preliminary"].ne("")
    changed = both & matched[metric + "_final"].ne(matched[metric + "_preliminary"])
    only_preliminary = sorted(set(map(tuple, preliminary[KEY].values)) - set(map(tuple, final[KEY].values)))

    # Parse numeric strings strictly; blanks are unknown, never zero.
    for field in COUNTS:
        values = final[field].str.strip()
        if not values.str.fullmatch(r"\d+|").all():
            raise ValueError(f"Unexpected numeric value in {field}")
        final[field] = pd.to_numeric(values.replace("", pd.NA), errors="raise").astype("Int64")

    medicaid, chip, combined, adult, child = COUNTS
    reconcilable = final[[medicaid, chip, combined]].notna().all(axis=1)
    if not final.loc[reconcilable, medicaid].add(final.loc[reconcilable, chip]).eq(final.loc[reconcilable, combined]).all():
        raise ValueError("Medicaid plus CHIP does not equal the combined reported total")
    for part, total in [(adult, medicaid), (child, combined)]:
        comparable = final[[part, total]].notna().all(axis=1)
        if not final.loc[comparable, part].le(final.loc[comparable, total]).all():
            raise ValueError(f"Enrollment subgroup exceeds its reported total: {part}")
    final["reporting_month"] = dates.loc[final.index].dt.strftime("%Y-%m-01")

    # Footnotes preserve CMS context, including special reporting caveats.
    footnotes = [field + "__footnotes" for field in COUNTS if field + "__footnotes" in final]
    columns = KEY + ["state_name", "reporting_month", "final_report", "preliminary_or_updated"] + COUNTS + footnotes
    silver = final[columns].sort_values(KEY).reset_index(drop=True)
    gaps = {}
    for state, group in silver.groupby("cga_state"):
        periods = pd.PeriodIndex(group.reporting_month, freq="M")
        missing_months = pd.period_range(periods.min(), periods.max(), freq="M").difference(periods)
        gaps[state] = [str(month) for month in missing_months]
    report = {
        "input_rows": len(raw), "input_columns": len(raw.columns),
        "raw_exact_duplicates": int(raw.duplicated().sum()),
        "raw_blank_counts": {field: int(raw[field].eq("").sum()) for field in raw.columns},
        "final_rows": len(silver), "preliminary_rows_excluded": len(preliminary),
        "matched_report_versions": len(matched), "matched_combined_counts_changed": int(changed.sum()),
        "preliminary_only_state_months": [list(key) for key in only_preliminary],
        "state_rows": {state: int(n) for state, n in silver.groupby("cga_state").size().items()},
        "period_start": silver.reporting_month.min(), "period_end": silver.reporting_month.max(),
        "missing_months_by_state": gaps,
        "final_missing_counts": {field: int(silver[field].isna().sum()) for field in COUNTS},
        "reconcilable_rows": int(reconcilable.sum()), "reconciliation_failures": 0,
        "validation": "passed",
    }
    return silver, report


def run(source, output, report_path):
    raw = pd.read_csv(source, dtype=str, keep_default_na=False)
    silver, report = clean(raw)
    output.mkdir(parents=True, exist_ok=True)
    csv_path = output / "cms_enrollment_clean.csv"
    parquet_path = output / "cms_enrollment_clean.parquet"
    silver.to_csv(csv_path, index=False)
    with duckdb.connect() as connection:
        connection.register("silver", silver)
        relation = connection.sql("SELECT * REPLACE (CAST(reporting_month AS DATE) AS reporting_month) FROM silver")
        relation.write_parquet(str(parquet_path), compression="zstd")
        actual = connection.read_parquet(str(parquet_path))
        if actual.count("*").fetchone()[0] != len(silver):
            raise ValueError("Parquet round-trip count mismatch")
        report["parquet_schema"] = dict(zip(actual.columns, map(str, actual.types)))
    report.update({"built_at_utc": datetime.now(timezone.utc).isoformat(), "source": str(source),
                   "source_sha256": digest(source),
                   "outputs": {str(path): digest(path) for path in [csv_path, parquet_path]}})
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=Path("data/processed/cms_enrollment_five_states.csv"))
    parser.add_argument("--output", type=Path, default=Path("data/silver"))
    parser.add_argument("--report", type=Path, default=Path("reports/enrollment_cleaning.json"))
    args = parser.parse_args()
    result = run(args.source, args.output, args.report)
    print(f"Enrollment Silver: {result['final_rows']} validated final state-month rows; {result['preliminary_rows_excluded']} preliminary rows excluded")
