"""Download and verify CMS-64 FMR and HHS provider spending public releases."""
import argparse
import csv
import hashlib
import json
import shutil
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from io import BytesIO
from pathlib import Path
from urllib.request import urlopen
from zipfile import ZipFile, ZIP_DEFLATED

from openpyxl import load_workbook

from acquire_public_data import STATES

YEARS = range(2018, 2026)
CMS_BASE = "https://www.medicaid.gov/medicaid/financial-management/downloads/"
HHS_BASE = "https://stopendataprod.blob.core.windows.net/datasets/"
HHS = {
    "medicaid-provider-spending.parquet": (
        HHS_BASE + "medicaid-provider-spending/2026-02-09/dataset/medicaid-provider-spending.parquet",
        3072545478, "f646d426126638dd0177cb14a86bfe7d7e9ed6b081a3e1c270bfe5070fb3fb94"),
    "medicaid-provider-spending-ndc.parquet": (
        HHS_BASE + "medicaid-provider-spending-ndc/2026-07-24/dataset/medicaid-provider-spending-ndc.parquet",
        234635252, "a8fe08f7bde9cb4090df1c9795428b57680f0ad643b9371dbf1490e871b7c782"),
}


def checksum(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def download(url, path, offline):
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.exists():
        if offline:
            raise FileNotFoundError(path)
        temporary = path.with_suffix(path.suffix + ".download")
        with urlopen(url, timeout=120) as response, temporary.open("wb") as output:
            shutil.copyfileobj(response, output, length=1024 * 1024)
        temporary.replace(path)
    return {"url": url, "path": str(path), "bytes": path.stat().st_size,
            "sha256": checksum(path)}


def parse_cms(year, root, offline):
    filename = f"financial-management-report-fy{year}.zip"
    path = root / "raw" / "cms64" / filename
    provenance = download(CMS_BASE + filename, path, offline)
    detail, totals = [], []
    with ZipFile(path) as archive:
        if archive.testzip() is not None:
            raise ValueError(f"Corrupt archive: {path}")
        provenance["members"] = archive.namelist()
        candidates = [name for name in archive.namelist() if name.endswith(".xlsx") and "CHIP" not in name.upper()]
        if len(candidates) != 1:
            raise ValueError(f"Unexpected workbook layout: {path}")
        workbook = load_workbook(BytesIO(archive.read(candidates[0])), read_only=True, data_only=True)
        try:
            for state, name in STATES.items():
                for prefix, program in [("MAP", "medical_assistance"), ("ADM", "administration")]:
                    sheet = workbook[f"{prefix} - {name}"]
                    iterator = iter(sheet.values)
                    for _ in range(6):
                        next(iterator)
                    headers = [" ".join(str(v).split()) if v is not None else "" for v in next(iterator)]
                    indices = [headers.index(label) for label in ["Service Category", "Total Computable", "Federal Share", "State Share"]]
                    found = []
                    for row_number, row in enumerate(iterator, 8):
                        category, total, federal, state_share = (row[i] for i in indices)
                        if not isinstance(category, str) or not isinstance(total, (int, float)):
                            continue
                        if not isinstance(federal, (int, float)) or not isinstance(state_share, (int, float)):
                            raise ValueError(f"Nonnumeric funding split: {year} {sheet.title} row {row_number}")
                        record = {"fiscal_year": year, "state": state, "program": program,
                                  "source_category": category, "source_row": row_number,
                                  "total_computable_usd": total, "federal_share_usd": federal,
                                  "state_share_usd": state_share, "source_workbook": candidates[0],
                                  "source_sheet": sheet.title}
                        detail.append(record)
                        if category.strip() == "Total Net Expenditures":
                            found.append(record)
                    if len(found) != 1:
                        raise ValueError(f"Expected one exact total line for {year} {sheet.title}")
                    totals.extend(found)
        finally:
            workbook.close()
    provenance["detail_rows"] = len(detail)
    provenance["total_rows"] = len(totals)
    return provenance, detail, totals


def write_csv(path, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def verify_hhs(root, offline):
    results = {}
    for filename, (url, size, digest) in HHS.items():
        path = root / "raw" / "hhs" / filename
        record = download(url, path, offline)
        if record["bytes"] != size or record["sha256"] != digest:
            raise ValueError(f"HHS published checksum/size mismatch: {filename}")
        with path.open("rb") as stream:
            if stream.read(4) != b"PAR1":
                raise ValueError(f"Invalid Parquet header: {filename}")
            stream.seek(-4, 2)
            if stream.read(4) != b"PAR1":
                raise ValueError(f"Invalid Parquet footer: {filename}")
        record["published_sha256_verified"] = True
        results[filename] = record
    return results


def run(root, report_path, bundle, offline, cms_only):
    with ThreadPoolExecutor(max_workers=4) as pool:
        results = list(pool.map(lambda year: parse_cms(year, root, offline), YEARS))
    detail = [row for _, rows, _ in results for row in rows]
    totals = [row for _, _, rows in results for row in rows]
    if len(totals) != len(YEARS) * len(STATES) * 2:
        raise ValueError("Unexpected total coverage")
    if len({(row["state"], row["fiscal_year"], row["program"]) for row in totals}) != len(totals):
        raise ValueError("Duplicate reported total lines")
    if any(row["total_computable_usd"] != row["federal_share_usd"] + row["state_share_usd"] for row in totals):
        raise ValueError("Reported total does not reconcile with federal and state shares")
    detail_path = root / "processed" / "cms64_five_state_detail.csv"
    total_path = root / "processed" / "cms64_five_state_reported_totals.csv"
    write_csv(detail_path, detail)
    write_csv(total_path, totals)
    report = {"built_at_utc": datetime.now(timezone.utc).isoformat(), "states": STATES,
              "fiscal_years": list(YEARS), "cms64_archives": [p for p, _, _ in results],
              "detail_rows": len(detail), "total_rows": len(totals), "total_funding_reconciliation": "passed",
              "outputs": {str(p): checksum(p) for p in [detail_path, total_path]},
              "hhs": {} if cms_only else verify_hhs(root, offline)}
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, indent=2) + "\n")
    if bundle:
        bundle.parent.mkdir(parents=True, exist_ok=True)
        with ZipFile(bundle, "w", ZIP_DEFLATED) as output:
            output.writestr("README.txt", "Care Gap Analytics — CMS-64 financial data\n"
                            "Official national archives: FY 2018–2025. Derived CSVs cover NY, NJ, MD, VA and PA.\n"
                            "The detail CSV preserves source line labels, including subtotals and adjustments. Do not sum all rows.\n"
                            "The reported totals CSV extracts the exact Total Net Expenditures lines from medical assistance and administration sheets.\n"
                            "These are program-level fiscal-year financial reports, not age-specific or patient-level claims.\n"
                            "See spending_data_acquisition.json for sources and checksums.\n")
            for provenance, _, _ in results:
                path = Path(provenance["path"])
                output.write(path, f"official_cms64/{path.name}")
            for path in [detail_path, total_path, report_path]:
                output.write(path, path.name)
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", type=Path, default=Path("data"))
    parser.add_argument("--report", type=Path, default=Path("reports/spending_data_acquisition.json"))
    parser.add_argument("--bundle", type=Path)
    parser.add_argument("--offline", action="store_true")
    parser.add_argument("--cms-only", action="store_true")
    args = parser.parse_args()
    result = run(args.data_dir, args.report, args.bundle, args.offline, args.cms_only)
    print(f"CMS-64: {result['detail_rows']} detail rows, {result['total_rows']} reported totals; HHS files verified: {len(result['hhs'])}")
