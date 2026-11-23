"""Acquire provider enrollment, NY Medicaid discharges and county context data."""
import argparse
import csv
import io
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlencode
from zipfile import ZipFile, ZIP_DEFLATED

import duckdb

from acquire_spending_data import download, checksum

FIPS = {"36": "NY", "34": "NJ", "24": "MD", "51": "VA", "42": "PA"}
PROVIDER_URL = "https://stopendataprod.blob.core.windows.net/datasets/medicaid-provider-enrollment-segments/2026-07-24/dataset/medicaid-provider-enrollment-segments.parquet"
PROVIDER_SHA = "c763c53946e5f8822e46db47d2cbd0de09c153c6b7045b57504c461afa2ce92a"
HRSA_BASE = "https://data.hrsa.gov/DataDownload/AHRF/"
ACS_BASE = "https://www2.census.gov/programs-surveys/acs/summary_file/2024/table-based-SF/data/5YRData/"
ACS_FIELDS = {"b01003": ("B01003_E001", "B01003_M001"),
              "b17001": ("B17001_E001", "B17001_M001", "B17001_E002", "B17001_M002"),
              "b19013": ("B19013_E001", "B19013_M001"),
              "b08201": ("B08201_E001", "B08201_M001", "B08201_E002", "B08201_M002")}
SPARCS_URL = "https://health.data.ny.gov/resource/sf4k-39ay.csv?" + urlencode({"$where": "payment_typology_1 = 'Medicaid'", "$limit": 700000, "$order": ":id"})


def csv_output(path, rows):
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def provider(root, processed, offline):
    source = root / "raw/hhs/medicaid-provider-enrollment-segments.parquet"
    metadata = download(PROVIDER_URL, source, offline)
    if metadata["bytes"] != 195945074 or metadata["sha256"] != PROVIDER_SHA:
        raise ValueError("Provider release checksum/size mismatch")
    output = processed / "provider_enrollment_five_states.parquet"
    with duckdb.connect() as db:
        relation = db.read_parquet(str(source))
        selected = relation.filter("STATE_CD IN ('NY','NJ','MD','VA','PA')")
        selected.write_parquet(str(output), compression="zstd")
        counts = selected.aggregate("STATE_CD, count(*) AS n", "STATE_CD").fetchall()
        metadata.update({"published_sha256_verified": True, "national_rows": relation.count("*").fetchone()[0],
                         "schema": dict(zip(relation.columns, map(str, relation.types))),
                         "state_rows": dict(counts), "output": str(output), "output_sha256": checksum(output)})
    if set(metadata["state_rows"]) != set(FIPS.values()):
        raise ValueError("Provider state coverage incomplete")
    return metadata, output


def county(root, processed, offline):
    raw = root / "raw/hrsa"
    archive = raw / "AHRF_2024-2025_CSV.zip"
    tech = raw / "AHRF_USER_TECH_2024-2025.zip"
    provenance = [download(HRSA_BASE + path.name, path, offline) for path in (archive, tech)]
    with ZipFile(archive) as z, ZipFile(tech) as documentation:
        if z.testzip() is not None or documentation.testzip() is not None:
            raise ValueError("Invalid HRSA archive")
        with io.TextIOWrapper(z.open(next(n for n in z.namelist() if n.endswith("/AHRF2025.csv"))), encoding="utf-8-sig") as stream:
            rows = [row for row in csv.DictReader(stream) if row["st_name_abbrev"] in FIPS.values()]
    keys = {row["fips_st_cnty"] for row in rows}
    if len(keys) != len(rows):
        raise ValueError("Duplicate HRSA county key")
    hrsa_output = processed / "ahrf_2024_2025_five_states.csv"
    csv_output(hrsa_output, rows)
    acs = {}
    acs_provenance = []
    for table, fields in ACS_FIELDS.items():
        path = root / "raw/acs" / f"acsdt5y2024-{table}.dat"
        acs_provenance.append(download(ACS_BASE + path.name, path, offline))
        found = {}
        with path.open(encoding="utf-8", newline="") as stream:
            for row in csv.DictReader(stream, delimiter="|"):
                geo = row["GEO_ID"]
                if geo.startswith("0500000US") and geo[9:11] in FIPS and len(geo) == 14:
                    county_fips = geo[9:]
                    if county_fips in found:
                        raise ValueError("Duplicate ACS county key")
                    found[county_fips] = {field: row[field] for field in fields}
        if set(found) != keys:
            raise ValueError(f"ACS/HRSA county coverage mismatch for {table}")
        for key, values in found.items():
            acs.setdefault(key, {"county_fips": key, "state": FIPS[key[:2]], "acs_period": "2020-2024"}).update(values)
    acs_output = processed / "acs_2020_2024_five_states.csv"
    csv_output(acs_output, [acs[key] for key in sorted(acs)])
    counts = dict(Counter(row["st_name_abbrev"] for row in rows))
    return {"hrsa_sources": provenance, "acs_sources": acs_provenance,
            "state_counties": counts, "hrsa_columns": len(rows[0]), "acs_fields": ACS_FIELDS,
            "matched_county_keys": len(keys), "outputs": {str(p): checksum(p) for p in (hrsa_output, acs_output)}}, [hrsa_output, acs_output, tech]


def hospital(root, offline):
    path = root / "raw/sparcs/sparcs_2024_medicaid_primary.csv"
    metadata = download(SPARCS_URL, path, offline)
    age = Counter()
    with path.open(encoding="utf-8-sig", newline="") as stream:
        reader = csv.DictReader(stream)
        for row in reader:
            if row["payment_typology_1"] != "Medicaid" or row["discharge_year"] != "2024":
                raise ValueError("Unexpected SPARCS payer or year")
            age[row["age_group"]] += 1
        metadata.update({"columns": reader.fieldnames, "rows": sum(age.values()), "age_groups": dict(age)})
    if metadata["rows"] != 635606:
        raise ValueError("SPARCS row count differs from observed 2024 payer query; review source refresh")
    return metadata, path


def run(root, report_path, bundle, offline, hospital_bundle=None):
    processed = root / "processed"
    processed.mkdir(parents=True, exist_ok=True)
    provider_report, provider_path = provider(root, processed, offline)
    county_report, county_paths = county(root, processed, offline)
    hospital_report, hospital_path = hospital(root, offline)
    report = {"built_at_utc": datetime.now(timezone.utc).isoformat(), "provider": provider_report,
              "county": county_report, "hospital": hospital_report}
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, indent=2) + "\n")
    if bundle:
        bundle.parent.mkdir(parents=True, exist_ok=True)
        with ZipFile(bundle, "w", ZIP_DEFLATED) as output:
            for path in [provider_path, *county_paths, report_path]:
                output.write(path, path.name)
            output.writestr("README.txt", "Five-state provider enrollment segments and county context data. Provider enrollment is not patient residence or claim state. ACS estimates and margins of error retain source codes. HRSA includes source technical documentation. See acquisition report. NY hospital data is available separately from the documented official API URL.\n")
    if hospital_bundle:
        hospital_bundle.parent.mkdir(parents=True, exist_ok=True)
        with ZipFile(hospital_bundle, "w", ZIP_DEFLATED) as output:
            output.write(hospital_path, hospital_path.name)
            output.write(report_path, report_path.name)
            output.writestr("README.txt", "Source: NY State Department of Health, SPARCS 2024 de-identified inpatient discharges. https://health.data.ny.gov/d/sf4k-39ay\n"
                            "Filtered by primary expected payer Medicaid. One row per discharge, not a unique person. Hospital charges/costs do not represent Medicaid payments. Source catalog license: Open Database License (ODbL), https://opendatacommons.org/licenses/odbl/1-0/.\n"
                            "Retain source attribution, reporting limitations, and privacy protections. Do not attempt to identify patients.\n")
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", type=Path, default=Path("data"))
    parser.add_argument("--report", type=Path, default=Path("reports/context_data_acquisition.json"))
    parser.add_argument("--bundle", type=Path)
    parser.add_argument("--hospital-bundle", type=Path)
    parser.add_argument("--offline", action="store_true")
    args = parser.parse_args()
    summary = run(args.data_dir, args.report, args.bundle, args.offline, args.hospital_bundle)
    print(json.dumps({"provider_state_rows": summary["provider"]["state_rows"], "county_count": summary["county"]["matched_county_keys"], "ny_hospital_rows": summary["hospital"]["rows"], "hospital_age_groups": summary["hospital"]["age_groups"]}, indent=2))
