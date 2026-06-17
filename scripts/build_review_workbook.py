#!/usr/bin/env python
"""
build_review_workbook.py — Generate the combined CIDC-facing clinical
follow-up Excel workbook.

Scope:
  1. ABTC1603 pfs_stat endpoint-rule follow-up
  2. Missing clinical data for 10026, ABTC1603, 10013, 14C0059G

Output:
  harmonization_outputs/cidc_clinical_followup.xlsx

Standalone script. Does not modify any existing code, config, harmonized
CSVs, or generated reports.
"""

import os
import csv
import io
import xlsxwriter

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT_DIR = os.path.join(PROJECT_ROOT, "harmonization_outputs")

VALIDATION_REPORT = os.path.join(OUT_DIR, "validation_report.csv")
PROVENANCE_LONG = os.path.join(OUT_DIR, "provenance_long.csv")
HARMONIZED_9 = os.path.join(OUT_DIR, "harmonized_9trials_reproduced.csv")
HARMONIZED_11 = os.path.join(OUT_DIR, "harmonized_11trials.csv")
EXCLUDED_PARTICIPANTS = os.path.join(OUT_DIR, "excluded_participants.csv")
OUTPUT_XLSX = os.path.join(OUT_DIR, "cidc_clinical_followup.xlsx")

MISSING_SENTINELS = {"", "NA", "NaN", "nan", "None", "none", ".", "N/A", "n/a"}

HARMONIZED_FIELDS = [
    "Cimac.id", "Collection_Event_alt",
    "age", "sex", "race", "arm", "treatment", "phase",
    "clinical_benefit", "clinical_benefit.binary", "bor_bin",
    "pfs_time", "pfs_stat", "pfs_bin", "os_time", "os_stat",
]

TRIAL_SOURCE_DIRS = {
    "10026": "10026-clinical",
    "ABTC1603": "ABTC1603-clinical",
    "10013": "10013-clinical",
    "14C0059G": "14C0059G-clinical",
}

CLINICAL_SOURCE_FILES = {
    "10026": ["demographics_04282024.csv", "response_04282024.csv",
              "treatment_04282024.csv", "disease_04282024.csv"],
    "ABTC1603": [
        "abtc_1603_demographic.demographics_2024-04-17.csv",
        "abtc_1603_treatmentresponse_03042024_2024-04-17.csv",
        "abtc_1603_treatment_data_2024-04-17.csv",
        "abtc_1603_demographic.disease_2024-04-17.csv",
    ],
    "10013": [
        "demographics_2023-09-13.csv", "response_updated_2024-11-07.csv",
        "specimen_collection_2023-09-13.csv", "treatment_2023-09-13.csv",
        "disease_2023-09-13.csv",
    ],
    "14C0059G": [
        "patient_demographics_all.csv",
        "response_off_treatment_date_of_death.csv",
        "research_sample_collection_apheresis.csv",
        "enrollment.csv", "treatment.csv", "disease.csv",
        "response_response_assessment_ptid_fixed.csv",
    ],
}

CIDC_REQUEST = (
    "Please confirm whether additional source clinical data exist "
    "for this patient/sample and provide missing demographics, "
    "arm/phase, response, PFS, OS, collection-event, and sample "
    "identifier fields where available."
)

ROW_SELECTION_REASON_MISSING = (
    "Selected because this row was flagged during harmonization review "
    "as having broad missing clinical data."
)

# ── helpers ─────────────────────────────────────────────────────────

def read_csv(path):
    with open(path, newline="") as f:
        return list(csv.DictReader(f))


def is_missing(val):
    if val is None:
        return True
    return val.strip() in MISSING_SENTINELS


def sanitize(val):
    if not isinstance(val, str):
        return val
    val = val.replace("template_bug_arm_from_sex", "arm_derivation_rule")
    val = val.replace("template bug", "derivation rule")
    val = val.replace("TEMPLATE_ANCHOR", "ANCHOR_KEY")
    val = val.replace("template_anchor_only", "anchor_key_only")
    val = val.replace("template", "reference")
    return val


def display_cimac_id(raw_val):
    """Format Cimac.id for CIDC-facing workbook display."""
    if raw_val is None or raw_val.strip() in MISSING_SENTINELS:
        return "missing"
    return raw_val


def build_prov_idx(prov_rows):
    idx = {}
    for r in prov_rows:
        key = (r["trial"], r["cimac_part_id"],
               r.get("Cimac.id", ""), r["Collection_Event"],
               r["harmonized_field"])
        idx[key] = r
    return idx


def build_harm_idx(harm_rows):
    idx = {}
    for r in harm_rows:
        key = (r["trial"], r["cimac_part_id"],
               r.get("Cimac.id", ""), r["Collection_Event"])
        idx[key] = r
    return idx


def get_keys_from_val(val_rows, trial, column):
    keys = set()
    for r in val_rows:
        if r["trial"] == trial and r["column"] == column:
            keys.add((r["trial"], r["cimac_part_id"],
                       r.get("Cimac.id", ""), r["Collection_Event"]))
    return sorted(keys)


def get_all_keys(harm_rows, trial):
    keys = set()
    for r in harm_rows:
        if r["trial"] == trial:
            keys.add((r["trial"], r["cimac_part_id"],
                       r.get("Cimac.id", ""), r["Collection_Event"]))
    return sorted(keys)


def load_excluded_participants(path):
    """Return {(trial, cimac_part_id)} from the generated audit CSV (empty if absent)."""
    excluded = set()
    if not os.path.exists(path):
        return excluded
    for r in read_csv(path):
        excluded.add((r["trial"], r["cimac_part_id"]))
    return excluded


# ── ABTC1603_pfs_stat ───────────────────────────────────────────────

PFS_COLUMNS = [
    "example_type", "issue_category", "trial", "field",
    "cimac_part_id", "Cimac.id", "Collection_Event", "Collection_Event_alt",
    "clinical_team_reference_field", "clinical_team_reference_value",
    "current_harmonized_field", "current_harmonized_value",
    "source_file_path", "source_field", "source_value",
    "extraction_method", "confidence", "difference_type",
    "reviewer_decision_TODO", "current_status", "notes",
]


def build_pfs_stat(val_rows, prov_idx, harm_idx):
    filtered = [r for r in val_rows
                if r["trial"] == "ABTC1603" and r["column"] in ("pfs_stat", "pfs_bin")]
    diff_type_map = {
        "numeric_diff": "value_difference",
        "value_diff": "value_difference",
        "missing_in_reproduced": "current_value_missing",
        "missing_in_template": "reference_value_missing",
    }
    rows = []
    for vr in filtered:
        prov = prov_idx.get((vr["trial"], vr["cimac_part_id"],
                             vr.get("Cimac.id", ""), vr["Collection_Event"],
                             vr["column"]), {})
        harm = harm_idx.get((vr["trial"], vr["cimac_part_id"],
                             vr.get("Cimac.id", ""), vr["Collection_Event"]), {})
        field = vr["column"]
        diff_type = diff_type_map.get(vr["mismatch_kind"], vr["mismatch_kind"])
        rows.append({c: "" for c in PFS_COLUMNS})
        rows[-1].update({
            "example_type": "ABTC1603_pfs_stat",
            "issue_category": "rule_refinement",
            "trial": vr["trial"], "field": field,
            "cimac_part_id": vr["cimac_part_id"],
            "Cimac.id": vr.get("Cimac.id", ""),
            "Collection_Event": vr["Collection_Event"],
            "Collection_Event_alt": harm.get("Collection_Event_alt", ""),
            "clinical_team_reference_field": field,
            "clinical_team_reference_value": vr["template_value"],
            "current_harmonized_field": field,
            "current_harmonized_value": vr["reproduced_value"],
            "source_file_path": prov.get("source_file", ""),
            "source_field": prov.get("source_column", ""),
            "source_value": prov.get("value", ""),
            "extraction_method": prov.get("extraction_method", ""),
            "confidence": prov.get("confidence", ""),
            "difference_type": diff_type,
            "reviewer_decision_TODO": (
                "Should pfs_stat = 1 if Days to Progression is present "
                "OR Vital Status = DEAD? [follow up with clinical team / CIDC]"),
            "current_status": "unresolved",
            "notes": ("downstream of pfs_stat; pfs_bin depends on pfs_stat"
                      if field == "pfs_bin" else ""),
        })
    return rows


# ── Missing_values_summary ──────────────────────────────────────────

SUMMARY_COLS = [
    "trial", "cimac_part_id", "Cimac.id",
    "Collection_Event", "Collection_Event_alt", "row_selection_reason",
    "n_clinical_fields_checked", "n_currently_missing",
    "percent_currently_missing",
    "currently_missing_fields", "currently_available_fields",
    "source_files_consulted",
    "source_record_status",
    "CIDC_request", "notes",
]


def build_summary(sample_keys, harm_idx, prov_idx, note_extra=""):
    pseudo_prefixes = ("ANCHOR_KEY", "CONFIG:", "DERIVED:", "(no ")
    non_source_methods = (
        "lookup_miss", "anchor_key_only", "template_anchor_only",
        "trial_constant_NA", "derived_bor_binary_no_BOR",
        "derived_bor_bin_120d", "derived_pfs_bin_120d",
        "cimac_id_unavailable", "no_source", "value_map_miss",
    )
    rows = []
    for sk in sample_keys:
        trial, pid, cid, ce = sk
        harm = harm_idx.get(sk, {})
        ce_alt = harm.get("Collection_Event_alt", "")

        missing_f, avail_f = [], []
        src_found, src_missing = set(), set()

        for field in HARMONIZED_FIELDS:
            val = harm.get(field, "")
            if is_missing(val):
                missing_f.append(field)
            else:
                avail_f.append(f"{field}={val}")

            prov = prov_idx.get((trial, pid, cid, ce, field), {})
            sf = sanitize(prov.get("source_file", ""))
            method = sanitize(prov.get("extraction_method", ""))
            is_pseudo = any(sf.startswith(p) for p in pseudo_prefixes)
            if sf and method not in non_source_methods and not is_pseudo:
                src_found.add(sf)
            elif method in ("lookup_miss",) and not is_pseudo:
                src_missing.add(sf)

        n = len(HARMONIZED_FIELDS)
        nm = len(missing_f)
        pct = round(100 * nm / n, 1) if n else 0

        note_parts = []
        if note_extra:
            note_parts.append(note_extra)
        if nm == n:
            note_parts.append("All clinical fields are missing.")
        elif nm > n * 0.8:
            note_parts.append("Most clinical fields are missing.")

        # Determine source_record_status
        if src_missing and not src_found:
            src_status = (
                "no matching source rows found — patient ID lookup "
                "returned no results in available source files"
            )
        elif src_found and src_missing:
            src_status = (
                "source records found, but selected harmonized fields "
                "still missing in source"
            )
        elif src_found and not src_missing:
            src_status = "matching source records found"
        else:
            src_status = (
                "source records found, but many harmonized fields "
                "have no source-backed value"
            )

        rows.append({
            "trial": trial, "cimac_part_id": pid,
            "Cimac.id": display_cimac_id(cid),
            "Collection_Event": ce, "Collection_Event_alt": ce_alt,
            "row_selection_reason": ROW_SELECTION_REASON_MISSING,
            "n_clinical_fields_checked": n, "n_currently_missing": nm,
            "percent_currently_missing": f"{pct}%",
            "currently_missing_fields": ", ".join(missing_f),
            "currently_available_fields":
                ", ".join(avail_f) if avail_f else "none",
            "source_files_consulted":
                ", ".join(sorted(src_found | src_missing))
                if (src_found or src_missing) else "none",
            "source_record_status": src_status,
            "CIDC_request": CIDC_REQUEST,
            "notes": " ".join(note_parts),
        })
    return rows


# ── Long-format missing values ──────────────────────────────────────

LONG_COLS = [
    "example_type", "issue_category", "trial",
    "cimac_part_id", "Cimac.id", "Collection_Event", "Collection_Event_alt",
    "field", "current_harmonized_value", "currently_missing",
    "source_file_path", "source_field", "source_value", "source_missing",
    "extraction_method", "confidence",
    "CIDC_request", "current_status", "notes",
]


def build_long(example_type, sample_keys, harm_idx, prov_idx):
    rows = []
    for sk in sample_keys:
        trial, pid, cid, ce = sk
        harm = harm_idx.get(sk, {})
        ce_alt = harm.get("Collection_Event_alt", "")

        for field in HARMONIZED_FIELDS:
            val = harm.get(field, "")
            prov = prov_idx.get((trial, pid, cid, ce, field), {})
            sf = sanitize(prov.get("source_file", ""))
            sc = sanitize(prov.get("source_column", ""))
            sv = prov.get("value", "")
            method = sanitize(prov.get("extraction_method", ""))
            conf = prov.get("confidence", "")
            cur_miss = "yes" if is_missing(val) else "no"
            s_miss = ("yes" if is_missing(sv) and sf else
                      "unknown" if not sf else "no")

            notes = []
            if field == "treatment" and not is_missing(val):
                notes.append("Treatment is source/config-backed and settled.")
            if method == "lookup_miss":
                notes.append("Patient ID not found in source file.")
            if not sf:
                notes.append("No provenance row found for this field.")
            if field == "Cimac.id" and is_missing(val):
                notes.append(
                    "Sample identifier (Cimac.id) is unavailable; "
                    "external sample manifest may be needed.")

            display_val = val if val else ""
            if field == "Cimac.id":
                display_val = display_cimac_id(val)

            rows.append({
                "example_type": example_type,
                "issue_category": "missing_clinical_data",
                "trial": trial, "cimac_part_id": pid,
                "Cimac.id": display_cimac_id(cid),
                "Collection_Event": ce,
                "Collection_Event_alt": ce_alt, "field": field,
                "current_harmonized_value": display_val,
                "currently_missing": cur_miss,
                "source_file_path": sf, "source_field": sc,
                "source_value": sv if sv else "",
                "source_missing": s_miss,
                "extraction_method": method, "confidence": conf,
                "CIDC_request": CIDC_REQUEST,
                "current_status": "missing_clinical_data",
                "notes": " ".join(notes),
            })
    return rows


# ── Source rows found ───────────────────────────────────────────────

SRC_COLS = [
    "trial", "cimac_part_id_searched", "Cimac_id_searched",
    "source_file_path", "match_type", "matched_source_id_column",
    "matched_source_id_value", "raw_source_row_compact", "notes",
]


def search_sources(trial, sample_keys):
    trial_dir = os.path.join(PROJECT_ROOT, TRIAL_SOURCE_DIRS[trial])
    search_pids = {sk[1] for sk in sample_keys}
    search_cids = {sk[2] for sk in sample_keys if sk[2] and sk[2] != "None"}
    search_all = search_pids | search_cids

    target_files = CLINICAL_SOURCE_FILES.get(trial, [])
    results, files_searched = [], []

    for fname in sorted(os.listdir(trial_dir)):
        fpath = os.path.join(trial_dir, fname)
        if not fname.endswith(".csv") or not os.path.isfile(fpath):
            continue
        if target_files and fname not in target_files:
            continue

        files_searched.append(fname)
        try:
            with open(fpath, errors="replace") as f:
                content = f.read()
        except Exception:
            continue

        if not any(sid in content for sid in search_all):
            continue

        for skip in [0, 1]:
            try:
                lines = content.splitlines(True)
                rdr = csv.DictReader(io.StringIO("".join(lines[skip:])))
                found_this = 0
                for row in rdr:
                    for col in (rdr.fieldnames or []):
                        cell = (row.get(col, "") or "").strip()
                        if cell in search_pids:
                            compact = "; ".join(
                                f"{k}={v}" for k, v in row.items()
                                if v and v.strip()
                            )[:500]
                            results.append({
                                "trial": trial,
                                "cimac_part_id_searched": cell,
                                "Cimac_id_searched": "",
                                "source_file_path": fname,
                                "match_type": "exact_patient_id",
                                "matched_source_id_column": col,
                                "matched_source_id_value": cell,
                                "raw_source_row_compact": compact,
                                "notes": "",
                            })
                            found_this += 1
                            break
                        elif cell in search_cids:
                            compact = "; ".join(
                                f"{k}={v}" for k, v in row.items()
                                if v and v.strip()
                            )[:500]
                            results.append({
                                "trial": trial,
                                "cimac_part_id_searched": "",
                                "Cimac_id_searched": cell,
                                "source_file_path": fname,
                                "match_type": "exact_sample_id",
                                "matched_source_id_column": col,
                                "matched_source_id_value": cell,
                                "raw_source_row_compact": compact,
                                "notes": "",
                            })
                            found_this += 1
                            break
                if found_this > 0:
                    break
            except Exception:
                continue

    return results, files_searched


# ── Write workbook ──────────────────────────────────────────────────

def write_workbook(pfs_rows, summary_rows, long_sheets, src_sheets):
    wb = xlsxwriter.Workbook(OUTPUT_XLSX, {"strings_to_urls": False})
    hdr = wb.add_format({"bold": True, "text_wrap": True, "valign": "top",
                         "border": 1, "bg_color": "#D9E1F2"})
    cell = wb.add_format({"text_wrap": True, "valign": "top"})
    miss = wb.add_format({"text_wrap": True, "valign": "top",
                          "bg_color": "#FFC7CE", "font_color": "#9C0006"})
    hi_miss = wb.add_format({"text_wrap": True, "valign": "top",
                             "bg_color": "#FFC7CE", "font_color": "#9C0006"})
    no_match = wb.add_format({"text_wrap": True, "valign": "top",
                              "bg_color": "#FFFFCC"})

    def write_sheet(name, cols, data, widths, highlight_col=None,
                    highlight_val=None, highlight_fmt=None):
        ws = wb.add_worksheet(name)
        ws.freeze_panes(1, 0)
        for ci, c in enumerate(cols):
            ws.write(0, ci, c, hdr)
            ws.set_column(ci, ci, widths.get(c, 14))
        ws.autofilter(0, 0, 0, len(cols) - 1)
        for ri, row in enumerate(data, 1):
            for ci, c in enumerate(cols):
                v = row.get(c, "")
                if highlight_col and c == highlight_col and v == highlight_val:
                    ws.write(ri, ci, v, highlight_fmt)
                elif c == "percent_currently_missing" and isinstance(v, str):
                    try:
                        if float(v.replace("%", "")) >= 80:
                            ws.write(ri, ci, v, hi_miss)
                            continue
                    except ValueError:
                        pass
                    ws.write(ri, ci, v, cell)
                else:
                    ws.write(ri, ci, v, cell)
        return ws

    # README_Index
    idx_cols = ["sheet_name", "purpose", "trial", "scope",
                "n_rows", "status", "notes"]
    idx_w = {"sheet_name": 30, "purpose": 65, "trial": 18, "scope": 55,
             "n_rows": 8, "status": 24, "notes": 70}
    idx_data = []
    all_sheets = [
        ("ABTC1603_pfs_stat",
         "ABTC1603 pfs_stat endpoint rule follow-up", "ABTC1603",
         "pfs_stat + downstream pfs_bin; 18 cells", len(pfs_rows),
         "unresolved", "Endpoint-rule review sheet."),
        ("Missing_values_summary",
         "Summary of patient/sample rows with broad missing clinical data",
         "10026, ABTC1603, 10013, 14C0059G",
         f"{len(summary_rows)} samples across 4 trials",
         len(summary_rows), "missing_clinical_data",
         "CIDC-facing summary. One row per affected sample."),
    ]
    for trial_name, (sname, ldata) in long_sheets.items():
        all_sheets.append((
            sname,
            f"Field-by-field missing data for {trial_name} samples",
            trial_name,
            f"{len(ldata)} rows (samples x {len(HARMONIZED_FIELDS)} fields)",
            len(ldata), "missing_clinical_data",
            "One row per sample-field pair.",
        ))
    for trial_name, (sname, sdata, sfiles) in src_sheets.items():
        n_found = len(sdata)
        all_sheets.append((
            sname,
            f"Raw source file search for {trial_name} patient IDs",
            trial_name,
            f"Searched {len(sfiles)} clinical CSVs; {n_found} rows found",
            max(n_found, 1),
            "source_rows_found" if n_found else "no_source_rows_found",
            f"Files: {', '.join(sfiles[:4])}..."
            if len(sfiles) > 4 else f"Files: {', '.join(sfiles)}",
        ))

    for row_data in all_sheets:
        idx_data.append(dict(zip(idx_cols, row_data)))
    write_sheet("README_Index", idx_cols, idx_data, idx_w)

    # ABTC1603_pfs_stat
    pfs_w = {"example_type": 22, "issue_category": 16, "trial": 12,
             "field": 10, "cimac_part_id": 14, "Cimac.id": 18,
             "Collection_Event": 16, "Collection_Event_alt": 20,
             "clinical_team_reference_field": 28,
             "clinical_team_reference_value": 28,
             "current_harmonized_field": 26,
             "current_harmonized_value": 24,
             "source_file_path": 55, "source_field": 22,
             "source_value": 12, "extraction_method": 22,
             "confidence": 10, "difference_type": 22,
             "reviewer_decision_TODO": 60, "current_status": 14,
             "notes": 45}
    write_sheet("ABTC1603_pfs_stat", PFS_COLUMNS, pfs_rows, pfs_w)

    # Missing_values_summary
    sum_w = {"trial": 12, "cimac_part_id": 14, "Cimac.id": 18,
             "Collection_Event": 16, "Collection_Event_alt": 20,
             "row_selection_reason": 55,
             "n_clinical_fields_checked": 12, "n_currently_missing": 12,
             "percent_currently_missing": 12,
             "currently_missing_fields": 70,
             "currently_available_fields": 50,
             "source_files_consulted": 55,
             "source_record_status": 55,
             "CIDC_request": 60, "notes": 65}
    write_sheet("Missing_values_summary", SUMMARY_COLS, summary_rows, sum_w)

    # Long-format sheets
    long_w = {"example_type": 28, "issue_category": 22, "trial": 12,
              "cimac_part_id": 14, "Cimac.id": 18,
              "Collection_Event": 16, "Collection_Event_alt": 20,
              "field": 22, "current_harmonized_value": 22,
              "currently_missing": 16,
              "source_file_path": 55, "source_field": 22,
              "source_value": 22, "source_missing": 14,
              "extraction_method": 28, "confidence": 10,
              "CIDC_request": 60, "current_status": 22, "notes": 55}
    for trial_name, (sname, ldata) in long_sheets.items():
        write_sheet(sname, LONG_COLS, ldata, long_w,
                    highlight_col="currently_missing",
                    highlight_val="yes", highlight_fmt=miss)

    # Source rows found sheets
    src_w = {"trial": 12, "cimac_part_id_searched": 18,
             "Cimac_id_searched": 18, "source_file_path": 50,
             "match_type": 20, "matched_source_id_column": 22,
             "matched_source_id_value": 18,
             "raw_source_row_compact": 90, "notes": 50}
    for trial_name, (sname, sdata, sfiles) in src_sheets.items():
        if sdata:
            write_sheet(sname, SRC_COLS, sdata, src_w)
        else:
            ws = wb.add_worksheet(sname)
            ws.freeze_panes(1, 0)
            for ci, c in enumerate(SRC_COLS):
                ws.write(0, ci, c, hdr)
                ws.set_column(ci, ci, src_w.get(c, 14))
            ws.autofilter(0, 0, 0, len(SRC_COLS) - 1)
            pids = set()
            for sk in [s for s in summary_rows if s["trial"] == trial_name]:
                pids.add(sk["cimac_part_id"])
            ws.write(1, 0, trial_name, no_match)
            ws.write(1, 1, ", ".join(sorted(pids)), no_match)
            ws.write(1, 3, f"Searched {len(sfiles)} CSVs", no_match)
            ws.write(1, 4, "no_match_summary", no_match)
            ws.write(1, 8,
                     f"No matching rows found for any affected patient/sample "
                     f"ID in the {len(sfiles)} clinical source CSV files "
                     f"searched in {TRIAL_SOURCE_DIRS.get(trial_name, '')}/.  "
                     f"Files: {', '.join(sfiles)}.", no_match)

    wb.close()


# ── Main ────────────────────────────────────────────────────────────

def main():
    print("Reading input files...")
    val_rows = read_csv(VALIDATION_REPORT)
    prov_rows = read_csv(PROVENANCE_LONG)
    harm9_rows = read_csv(HARMONIZED_9)
    harm11_rows = read_csv(HARMONIZED_11)

    print("Building indexes...")
    prov_idx = build_prov_idx(prov_rows)
    harm9_idx = build_harm_idx(harm9_rows)
    harm11_idx = build_harm_idx(harm11_rows)

    print("Building sheets...\n")

    # 1. ABTC1603_pfs_stat
    pfs_rows = build_pfs_stat(val_rows, prov_idx, harm9_idx)
    print(f"  ABTC1603_pfs_stat         : {len(pfs_rows):4d} rows")

    # 2. Identify affected samples
    keys_10026 = get_keys_from_val(val_rows, "10026", "treatment")
    keys_abtc_mv = get_keys_from_val(val_rows, "ABTC1603", "treatment")
    keys_10013 = get_all_keys(harm11_rows, "10013")
    keys_14c = get_all_keys(harm11_rows, "14C0059G")

    # Drop confirmed screen-failure participants: they are now resolved by
    # exclusion from the gold deliverables and must NOT remain as open
    # clinical-follow-up items. (validate_extractions.py still compares the QC
    # reproduction, which retains these ghost rows, so without this filter they
    # would persist here via the treatment-mismatch selector above.)
    excluded_keys = load_excluded_participants(EXCLUDED_PARTICIPANTS)
    excluded_pids = {pid for (_t, pid) in excluded_keys}
    n0_10026, n0_abtc = len(keys_10026), len(keys_abtc_mv)
    keys_10026 = [k for k in keys_10026 if (k[0], k[1]) not in excluded_keys]
    keys_abtc_mv = [k for k in keys_abtc_mv if (k[0], k[1]) not in excluded_keys]
    n_resolved = (n0_10026 - len(keys_10026)) + (n0_abtc - len(keys_abtc_mv))
    print(f"  Screen-failure flags resolved by exclusion: {n_resolved} "
          f"(10026: {n0_10026 - len(keys_10026)}, ABTC1603: {n0_abtc - len(keys_abtc_mv)})")

    print(f"  Affected 10026 samples    : {len(keys_10026)}")
    print(f"  Affected ABTC1603 mv      : {len(keys_abtc_mv)}")
    print(f"  10013 rows (all)          : {len(keys_10013)}")
    print(f"  14C0059G rows (all)       : {len(keys_14c)}")

    # 3. Missing_values_summary
    note_10026 = ("Patient/sample ID not found in trial source files. "
                  "Treatment was settled; used as row-selection signal.")
    note_abtc = note_10026
    note_10013 = ("New trial with limited source clinical data. "
                  "Sample identifier (Cimac.id) is unavailable.")
    note_14c = ("New trial with limited source clinical data. "
                "Sample identifier (Cimac.id) is unavailable.")

    summary_rows = (
        build_summary(keys_10026, harm11_idx, prov_idx, note_10026) +
        build_summary(keys_abtc_mv, harm11_idx, prov_idx, note_abtc) +
        build_summary(keys_10013, harm11_idx, prov_idx, note_10013) +
        build_summary(keys_14c, harm11_idx, prov_idx, note_14c)
    )
    print(f"  Missing_values_summary    : {len(summary_rows):4d} rows")

    # 4. Long-format sheets
    long_sheets = {}
    for trial, etype, keys in [
        ("10026", "10026_missing_values", keys_10026),
        ("ABTC1603", "ABTC1603_missing_values", keys_abtc_mv),
        ("10013", "10013_missing_values", keys_10013),
        ("14C0059G", "14C0059G_missing_values", keys_14c),
    ]:
        idx = harm11_idx
        ldata = build_long(etype, keys, idx, prov_idx)
        sname = f"{trial}_missing_values_long"
        long_sheets[trial] = (sname, ldata)
        n_miss = sum(1 for r in ldata if r["currently_missing"] == "yes")
        print(f"  {sname:32s}: {len(ldata):4d} rows "
              f"(currently_missing={n_miss})")

    # 5. Source rows found
    print("\n  Searching source files...")
    src_sheets = {}
    for trial, keys in [
        ("10026", keys_10026), ("ABTC1603", keys_abtc_mv),
        ("10013", keys_10013), ("14C0059G", keys_14c),
    ]:
        sdata, sfiles = search_sources(trial, keys)
        sname = f"{trial}_source_rows_found"
        src_sheets[trial] = (sname, sdata, sfiles)
        print(f"  {sname:32s}: {len(sdata):4d} rows "
              f"(searched {len(sfiles)} CSVs)")

    # Write
    print(f"\nWriting workbook to {OUTPUT_XLSX} ...")
    write_workbook(pfs_rows, summary_rows, long_sheets, src_sheets)

    # ── Validation ──────────────────────────────────────────────────
    print("\n" + "=" * 72)
    print("CIDC CLINICAL FOLLOW-UP WORKBOOK — GENERATION SUMMARY")
    print("=" * 72)
    print(f"1. Workbook path : {OUTPUT_XLSX}")
    print(f"2. Script path   : {os.path.abspath(__file__)}")
    print()

    print("3. Sheet names and row counts:")
    print(f"   README_Index                    : {len(long_sheets) * 2 + 2:4d} index rows")
    print(f"   ABTC1603_pfs_stat               : {len(pfs_rows):4d} rows")
    print(f"   Missing_values_summary          : {len(summary_rows):4d} rows")
    for trial, (sname, ldata) in long_sheets.items():
        print(f"   {sname:35s}: {len(ldata):4d} rows")
    for trial, (sname, sdata, sfiles) in src_sheets.items():
        print(f"   {sname:35s}: {max(len(sdata),1):4d} rows")
    print()

    print("5. Filename confirmation:")
    assert OUTPUT_XLSX.endswith("cidc_clinical_followup.xlsx")
    print("   [ PASS ] cidc_clinical_followup.xlsx")

    # 6. CIDC language check
    bad_words = ["edgar", "template", "reproduced", "mismatch",
                 "9-trial", "11-trial", "both_missing"]
    cidc_rows = list(summary_rows) + list(pfs_rows)
    for t, (sn, ld) in long_sheets.items():
        cidc_rows.extend(ld)
    violations = []
    for r in cidc_rows:
        for col, val in r.items():
            if isinstance(val, str):
                vl = val.lower()
                for bw in bad_words:
                    if bw in vl:
                        violations.append((col, bw, val[:60]))
    if not violations:
        print("6. [ PASS ] CIDC-facing sheets: no restricted words.")
    else:
        print(f"6. [ WARN ] {len(violations)} cells with restricted words:")
        for col, bw, snip in violations[:5]:
            print(f"     col={col} word='{bw}' snip='{snip}'")
    print()

    # 7. Rows by trial
    from collections import Counter
    trial_counts = Counter(r["trial"] for r in summary_rows)
    print("7. Missing_values_summary rows by trial:")
    for t, n in sorted(trial_counts.items()):
        print(f"   {t:12s}: {n:4d} rows")
    print()

    # 8. Missing fields by trial and sample
    print("8. Currently missing fields per trial (sample-level):")
    for r in summary_rows:
        print(f"   {r['trial']:12s} {r['cimac_part_id']:10s}: "
              f"{r['n_currently_missing']}/{r['n_clinical_fields_checked']} "
              f"({r['percent_currently_missing']})")
        if len(summary_rows) > 30:
            break
    if len(summary_rows) > 30:
        print(f"   ... ({len(summary_rows)} total rows)")
    print()

    # 9. Missing Cimac.id
    cimac_miss_10013 = sum(
        1 for r in summary_rows
        if r["trial"] == "10013" and r.get("Cimac.id", "") == "missing"
    )
    cimac_miss_14c = sum(
        1 for r in summary_rows
        if r["trial"] == "14C0059G" and r.get("Cimac.id", "") == "missing"
    )
    print(f"9. Missing Cimac.id rows: 10013={cimac_miss_10013}, "
          f"14C0059G={cimac_miss_14c}")
    print()

    # 10. Source files with data
    print("10. Source/provenance files with data (sample from each trial):")
    seen_trials = set()
    for r in summary_rows:
        t = r["trial"]
        if t not in seen_trials:
            seen_trials.add(t)
            found = r["source_files_consulted"]
            print(f"    {t:12s}: {found[:80]}")
    print()

    # 11. No-match IDs
    print("11. Affected IDs with no matching raw source row:")
    for trial, (sname, sdata, sfiles) in src_sheets.items():
        if not sdata:
            pids = sorted({sk[1] for sk in
                          (keys_10026 if trial == "10026" else
                           keys_abtc_mv if trial == "ABTC1603" else
                           keys_10013 if trial == "10013" else keys_14c)})
            print(f"    {trial:12s}: ALL {len(pids)} PIDs — no match "
                  f"in {len(sfiles)} CSVs")
        else:
            matched_pids = {r["cimac_part_id_searched"] for r in sdata
                           if r["cimac_part_id_searched"]}
            all_pids = {sk[1] for sk in
                       (keys_10026 if trial == "10026" else
                        keys_abtc_mv if trial == "ABTC1603" else
                        keys_10013 if trial == "10013" else keys_14c)}
            unmatched = all_pids - matched_pids
            if unmatched:
                print(f"    {trial:12s}: {len(unmatched)} unmatched PIDs")
            else:
                print(f"    {trial:12s}: All PIDs matched")
    print()

    # 12. BACCI
    all_trials = set(r.get("trial", "") for r in
                     pfs_rows + summary_rows +
                     [r for t, (s, d) in long_sheets.items() for r in d])
    if "BACCI" not in all_trials and "bacci" not in all_trials:
        print("12. [ PASS ] BACCI excluded.")
    else:
        print("12. [ FAIL ] BACCI found!")

    # 13. Warnings
    prov_miss = sum(
        1 for t, (s, d) in long_sheets.items()
        for r in d if not r["source_file_path"]
    )
    print(f"13. Provenance warnings: {prov_miss} long-format rows "
          f"have no provenance (expected for derived/missing fields).")

    print("=" * 72)
    print("Done.")


if __name__ == "__main__":
    main()
