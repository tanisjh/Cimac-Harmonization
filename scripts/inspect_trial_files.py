"""
inspect_trial_files.py — Build a file inventory of every *-clinical/ trial directory.

Outputs (under harmonization_outputs/):
  - file_inventory.csv         one row per source file with classification + metadata
  - headers_by_file.json       per-file column headers and row counts for tabular files
  - duplicate_files.csv        groups of files with identical sha256 content
  - inspect_summary.txt        per-trial human-readable summary
"""
from __future__ import annotations

import argparse
import hashlib
import json
import logging
import re
import sys
from collections import defaultdict
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from lib.cidc_io import read_cidc_csv  # noqa: E402

LOG = logging.getLogger("inspect_trial_files")

PROJECT_ROOT = Path(__file__).resolve().parent.parent
OUTPUT_DIR = PROJECT_ROOT / "harmonization_outputs"

DOMAIN_KEYWORDS = {
    "demographics":         ["demographic", "patient_demo", "demo"],
    "disease":              ["disease", "histology", "disease_specific", "mm_staging", "mds_raeb", "extend_of_disease", "ext_of_disease"],
    "history":              ["history", "comorbidit", "patient_history", "transplant_history", "prior_therapy", "prior_radiation", "prior_surgery", "prior_treatment_summary", "baseline_medical_history", "baseline_abnormalities", "patient_prior_ae", "history_description"],
    "response":             ["response", "best_response", "treatmentresponse", "resp_out"],
    "survival_death":       ["death", "on_study_death", "off_treatment", "response_off_treatment_date_of_death"],
    "treatment":            ["treatment", "drug_administration", "infusion", "treatment_dose", "additional_treatment", "onstudyprisystx"],
    "adverse_event":        ["adverse", "late_ae", "bsl_ae", "toxicity"],
    "sample_collection":    ["sample_collection", "specimen_collection", "days_to_collection_event", "days_from_registration", "cimac_samples"],
    "id_linkage":           ["id_linkage", "id linkage", "cimac_part_id_linkage", "linkage"],
    "molecular":            ["molecular", "cytogenetics", "msi_status", "tmb", "ngs", "pd_l1", "pdl1"],
    "arm_enrollment":       ["arm", "enrollment_assignment", "armc_subgroup", "armaandb", "enrollment"],
    "labs":                 ["lab", "all_labs"],
    "course_dates":         ["course_dates", "course_init", "all_course_dates"],
    "gvhd":                 ["gvhd"],
    "mri":                  ["mri"],
    "pathology":            ["pathology", "neuropsychological"],
    "procedure":            ["procedure", "apheresis"],
    "transfer":             ["transfer"],
}

DATA_DICT_PAT  = re.compile(r"data[_ ]?dictionary|variable[_ ]?definitions|variable[_ ]?list|data[_ ]?guide", re.I)
CIDC_ANNOT_PAT = re.compile(r"cidc[_ ]annotation", re.I)
APPENDIX_PAT   = re.compile(r"appendix", re.I)
FORMATS_PAT    = re.compile(r"^formats", re.I)
FIELD_LOC_PAT  = re.compile(r"field[_ ]?locations?", re.I)

DATE_PAT = re.compile(
    r"""(
        \d{4}[-_.]\d{2}[-_.]\d{2}     | # 2023-09-13
        \d{2}[-_.]\d{2}[-_.]\d{4}     | # 09-13-2023
        \d{8}                         | # 20230913
        \d{2}\d{2}\d{4}                 # 09132023
    )""",
    re.X,
)


def classify(name: str) -> tuple[str, str]:
    """Return (role, domain) for a filename. role in {data_dict, cidc_annotation, appendix, formats, field_locations, domain, unknown}."""
    base = name.lower()
    if DATA_DICT_PAT.search(name):  return ("data_dict", "")
    if CIDC_ANNOT_PAT.search(name): return ("cidc_annotation", "")
    if APPENDIX_PAT.search(name):   return ("appendix", "")
    if FORMATS_PAT.search(name):    return ("formats", "")
    if FIELD_LOC_PAT.search(name):  return ("field_locations", "")
    for domain, kws in DOMAIN_KEYWORDS.items():
        if any(kw in base for kw in kws):
            return ("domain", domain)
    return ("unknown", "")


def extract_date_tag(name: str) -> str:
    matches = DATE_PAT.findall(name)
    return matches[-1] if matches else ""


def sha256_file(path: Path, chunk: int = 1 << 16) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        while True:
            b = f.read(chunk)
            if not b:
                break
            h.update(b)
    return h.hexdigest()


def safe_read_csv_head(path: Path):
    """Return (columns, n_rows, encoding, preamble, err) for a CSV.

    Uses the CIDC-aware reader so the 1-line preamble convention is detected
    and skipped automatically.
    """
    r = read_cidc_csv(path)
    if r.note and r.df.empty:
        return [], 0, r.encoding, r.preamble_skipped, r.note
    return list(r.df.columns), int(len(r.df)), r.encoding, r.preamble_skipped, None


def safe_read_excel_sheets(path: Path):
    """Return list of {sheet, columns, n_rows} for every sheet."""
    try:
        xl = pd.ExcelFile(path)
    except Exception as e:
        return [], f"{type(e).__name__}: {e}"
    out = []
    for sn in xl.sheet_names:
        try:
            df = xl.parse(sn, nrows=5)  # cheap read for headers
            ncols = list(df.columns)
            # then count rows efficiently
            df_full = xl.parse(sn)
            out.append({"sheet": sn, "columns": [str(c) for c in ncols], "n_rows": int(len(df_full))})
        except Exception as e:
            out.append({"sheet": sn, "columns": [], "n_rows": 0, "error": f"{type(e).__name__}: {e}"})
    return out, None


def inspect_trial_dir(trial_dir: Path):
    """Yield one record per file in the trial directory."""
    for p in sorted(trial_dir.iterdir()):
        if not p.is_file():
            continue
        rec = {
            "trial_dir": trial_dir.name,
            "trial_slug": trial_dir.name.removesuffix("-clinical"),
            "filename": p.name,
            "size_bytes": p.stat().st_size,
            "ext": p.suffix.lower().lstrip("."),
            "date_tag": extract_date_tag(p.name),
            "sha256": "",
            "role": "",
            "domain": "",
            "n_rows": 0,
            "n_cols": 0,
            "sheet_count": 0,
            "error": "",
        }
        role, domain = classify(p.name)
        rec["role"], rec["domain"] = role, domain
        try:
            rec["sha256"] = sha256_file(p)
        except Exception as e:
            rec["error"] = f"hash:{type(e).__name__}"
        yield rec, p


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=str(PROJECT_ROOT), help="repo root (default: parent of scripts/)")
    ap.add_argument("--out", default=str(OUTPUT_DIR))
    ap.add_argument("-v", "--verbose", action="store_true")
    args = ap.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
    )

    root = Path(args.root)
    outdir = Path(args.out)
    outdir.mkdir(parents=True, exist_ok=True)

    trial_dirs = sorted([p for p in root.iterdir() if p.is_dir() and p.name.endswith("-clinical")])
    LOG.info("Found %d trial directories under %s", len(trial_dirs), root)

    inventory = []
    headers_by_file: dict[str, dict] = {}
    hash_groups: dict[str, list[str]] = defaultdict(list)

    for td in trial_dirs:
        LOG.info("Inspecting %s", td.name)
        for rec, p in inspect_trial_dir(td):
            if rec["ext"] == "csv":
                cols, n_rows, enc, preamble, err = safe_read_csv_head(p)
                rec["n_rows"], rec["n_cols"] = n_rows, len(cols)
                rec["preamble"] = bool(preamble)
                if err:
                    rec["error"] = (rec["error"] + ";" + err).strip(";")
                headers_by_file[f"{td.name}/{p.name}"] = {
                    "role": rec["role"],
                    "domain": rec["domain"],
                    "date_tag": rec["date_tag"],
                    "sha256": rec["sha256"],
                    "encoding": enc,
                    "preamble": bool(preamble),
                    "n_rows": n_rows,
                    "columns": cols,
                }
            elif rec["ext"] in ("xlsx", "xls"):
                sheets, err = safe_read_excel_sheets(p)
                rec["sheet_count"] = len(sheets)
                rec["n_rows"]      = sum(s.get("n_rows", 0) for s in sheets)
                rec["n_cols"]      = max((len(s.get("columns", [])) for s in sheets), default=0)
                if err:
                    rec["error"] = (rec["error"] + ";" + err).strip(";")
                headers_by_file[f"{td.name}/{p.name}"] = {
                    "role": rec["role"],
                    "domain": rec["domain"],
                    "date_tag": rec["date_tag"],
                    "sha256": rec["sha256"],
                    "sheets": sheets,
                }
            else:
                headers_by_file[f"{td.name}/{p.name}"] = {
                    "role": rec["role"],
                    "domain": rec["domain"],
                    "date_tag": rec["date_tag"],
                    "sha256": rec["sha256"],
                }
            if rec["sha256"]:
                hash_groups[rec["sha256"]].append(f"{td.name}/{p.name}")
            inventory.append(rec)

    # Write inventory
    inv_path = outdir / "file_inventory.csv"
    pd.DataFrame(inventory).to_csv(inv_path, index=False)
    LOG.info("Wrote %s (%d rows)", inv_path, len(inventory))

    # Write duplicates report
    dup_rows = []
    for h, paths in hash_groups.items():
        if len(paths) > 1:
            for p in paths:
                dup_rows.append({"sha256": h, "path": p, "group_size": len(paths)})
    dup_path = outdir / "duplicate_files.csv"
    pd.DataFrame(dup_rows).to_csv(dup_path, index=False)
    LOG.info("Wrote %s (%d duplicate paths in %d groups)",
             dup_path, len(dup_rows), sum(1 for v in hash_groups.values() if len(v) > 1))

    # Write headers JSON
    hdr_path = outdir / "headers_by_file.json"
    hdr_path.write_text(json.dumps(headers_by_file, indent=2, default=str))
    LOG.info("Wrote %s", hdr_path)

    # Per-trial summary
    inv_df = pd.DataFrame(inventory)
    summary_lines = []
    for td in trial_dirs:
        sub = inv_df[inv_df["trial_dir"] == td.name]
        if sub.empty:
            continue
        summary_lines.append(f"\n=== {td.name} ({len(sub)} files) ===")
        # role counts
        role_counts = sub["role"].value_counts().to_dict()
        summary_lines.append("  roles: " + ", ".join(f"{k}={v}" for k, v in role_counts.items()))
        # domain counts
        dom_counts = sub[sub["role"] == "domain"]["domain"].value_counts().to_dict()
        if dom_counts:
            summary_lines.append("  domains: " + ", ".join(f"{k}={v}" for k, v in dom_counts.items()))
        # latest snapshot per (role, domain)
        latest_by_kind = (
            sub.assign(kind=sub["role"] + "/" + sub["domain"])
               .sort_values("date_tag")
               .groupby("kind", as_index=False)
               .tail(1)
               [["kind", "filename", "date_tag", "n_rows", "n_cols", "sheet_count"]]
        )
        summary_lines.append("  latest snapshot per kind:")
        for _, r in latest_by_kind.iterrows():
            summary_lines.append(f"    {r['kind']:35s} -> {r['filename']} (date={r['date_tag']}, rows={r['n_rows']}, cols={r['n_cols']}, sheets={r['sheet_count']})")

    sum_path = outdir / "inspect_summary.txt"
    sum_path.write_text("\n".join(summary_lines))
    LOG.info("Wrote %s", sum_path)


if __name__ == "__main__":
    main()
