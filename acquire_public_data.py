"""Acquire official CMS aggregate quality and enrollment data for five states."""
import argparse
import csv
import hashlib
import json
import sqlite3
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import urlopen

STATES = {"NY": "New York", "NJ": "New Jersey", "MD": "Maryland", "VA": "Virginia", "PA": "Pennsylvania"}
SOURCES = {
    "quality": ("a5023394-ab10-465b-bb4a-7de5ac98d90c", "state"),
    "enrollment": ("6165f45b-ca93-5bb5-9d06-db29c692a360", "state_abbreviation"),
}


def acquire(source, state, raw_dir, offline=False):
    dataset, field = SOURCES[source]
    value = STATES[state] if source == "quality" else state
    params = {"conditions[0][property]": field, "conditions[0][value]": value,
              "conditions[0][operator]": "=", "limit": 500}
    url = f"https://data.medicaid.gov/api/1/datastore/query/{dataset}/0?{urlencode(params)}"
    path = raw_dir / f"{source}_{state}.json"
    if offline:
        raw = path.read_bytes()
    else:
        with urlopen(url, timeout=60) as response:
            raw = response.read()
    payload = json.loads(raw)
    rows = payload["results"]
    if len(rows) != payload["count"] or not rows or any(row[field] != value for row in rows):
        raise ValueError(f"Incomplete or invalid state response: {source}/{state}")
    if not offline:
        path.write_bytes(raw)
    return source, state, rows, {
        "url": url, "file": str(path), "bytes": len(raw),
        "sha256": hashlib.sha256(raw).hexdigest(), "rows": len(rows),
        "snapshot_file_modified_utc": datetime.fromtimestamp(path.stat().st_mtime, timezone.utc).isoformat(),
        "schema": payload.get("schema", {}),
    }


def run(root, report_path, offline=False):
    raw_dir = root / "raw" / "cms"
    processed = root / "processed"
    raw_dir.mkdir(parents=True, exist_ok=True)
    processed.mkdir(parents=True, exist_ok=True)
    with ThreadPoolExecutor(max_workers=5) as pool:
        results = list(pool.map(lambda pair: acquire(*pair, raw_dir, offline),
                                [(s, state) for s in SOURCES for state in STATES]))
    report = {"built_at_utc": datetime.now(timezone.utc).isoformat(), "offline_rebuild": offline,
              "states": STATES, "datasets": {}}
    tables = {}
    for source in SOURCES:
        combined = []
        entries = {}
        for name, state, rows, provenance in results:
            if name != source:
                continue
            combined.extend({"cga_state": state, **row} for row in rows)
            entries[state] = provenance
        fields = list(combined[0])
        if any(set(row) != set(fields) for row in combined):
            raise ValueError(f"Schema mismatch in {source}")
        csv_path = processed / f"cms_{source}_five_states.csv"
        with csv_path.open("w", newline="", encoding="utf-8") as stream:
            writer = csv.DictWriter(stream, fieldnames=fields)
            writer.writeheader()
            writer.writerows(combined)
        period = "core_set_year" if source == "quality" else "reporting_period"
        report["datasets"][source] = {
            "dataset_id": SOURCES[source][0], "rows": len(combined),
            "periods": sorted({row[period] for row in combined if row[period]}),
            "columns": fields, "state_rows": {s: v["rows"] for s, v in entries.items()},
            "source_responses": entries,
            "output": str(csv_path), "output_sha256": hashlib.sha256(csv_path.read_bytes()).hexdigest(),
            "missing_values": {f: sum(row[f] in (None, "") for row in combined) for f in fields},
        }
        if source == "quality":
            report["datasets"][source]["reporting_programs"] = sorted({r["reporting_program"] for r in combined})
            report["datasets"][source]["state_rate_flags"] = dict(Counter(r["state_rate"] for r in combined if not str(r["state_rate"]).replace(".", "", 1).isdigit()))
            report["datasets"][source]["program_rows"] = dict(Counter(r["reporting_program"] for r in combined))
            if set(report["datasets"][source]["state_rate_flags"]) - {"DS", "NPR", "NA", "#"}:
                raise ValueError("Unrecognized quality-rate flag; review source before analysis")
        else:
            finals = [r for r in combined if r["final_report"] == "Y"]
            keys = [(r["cga_state"], r["reporting_period"]) for r in finals]
            if len(keys) != len(set(keys)):
                raise ValueError("Duplicate final state/month enrollment rows")
            report["datasets"][source]["final_rows"] = len(finals)
            report["datasets"][source]["final_periods"] = sorted({r["reporting_period"] for r in finals})
        schema = entries[next(iter(entries))]["schema"]
        if any(entry["schema"] != schema for entry in entries.values()):
            raise ValueError(f"Source schema mismatch in {source}")
        report["datasets"][source]["schema"] = schema
        for entry in entries.values():
            del entry["schema"]
        tables[source] = combined
    database = processed / "cga_public.sqlite"
    temporary = processed / "cga_public.build.sqlite"
    if temporary.exists():
        temporary.unlink()
    with sqlite3.connect(temporary) as connection:
        for name, rows in tables.items():
            fields = list(rows[0])
            definitions = ", ".join(f'"{field}" TEXT' for field in fields)
            connection.execute(f"CREATE TABLE cms_{name} ({definitions})")
            placeholders = ", ".join("?" for _ in fields)
            connection.executemany(f"INSERT INTO cms_{name} VALUES ({placeholders})",
                                   ([row[field] for field in fields] for row in rows))
        connection.execute("CREATE VIEW enrollment_final AS SELECT * FROM cms_enrollment WHERE final_report = 'Y'")
        connection.execute("CREATE VIEW quality_reported AS SELECT * FROM cms_quality WHERE state_rate NOT IN ('DS', 'NPR', 'NA', '#') AND state_rate IS NOT NULL AND state_rate != ''")
        report["database"] = {"path": str(database), "integrity": connection.execute("PRAGMA integrity_check").fetchone()[0],
                              "quality_reported_rows": connection.execute("SELECT COUNT(*) FROM quality_reported").fetchone()[0],
                              "enrollment_final_rows": connection.execute("SELECT COUNT(*) FROM enrollment_final").fetchone()[0]}
    temporary.replace(database)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", type=Path, default=Path("data"))
    parser.add_argument("--report", type=Path, default=Path("reports/public_data_acquisition.json"))
    parser.add_argument("--offline", action="store_true", help="Rebuild from previously downloaded JSON snapshots")
    args = parser.parse_args()
    result = run(args.data_dir, args.report, args.offline)
    for name, summary in result["datasets"].items():
        print(f"{name}: {summary['rows']} rows across {len(summary['state_rows'])} states")
