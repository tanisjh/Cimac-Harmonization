"""
build_review_checklist.py — Produce a prioritized human-review checklist.

Reads existing pipeline outputs (validation_summary.csv, flagged_for_review.csv,
provenance_long.csv) and synthesizes a prioritized list of (trial, field) items
that need human attention before further iteration.

Outputs:
  harmonization_outputs/review_priority_checklist.csv
  harmonization_outputs/review_priority_checklist.md

Does NOT modify harmonized outputs or any source data.
"""
from __future__ import annotations

import argparse
import logging
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parent.parent
OUTDIR       = PROJECT_ROOT / "harmonization_outputs"

LOG = logging.getLogger("checklist")


# ── Hand-authored items where the issue is qualitative / cross-trial ──────
# Each entry is a dict with the same schema as the auto-generated rows.
# These augment what we infer from validation_summary / flagged_for_review.
MANUAL_ITEMS: list[dict] = [
    {
        "priority": "P3",
        "trial": "ALL (9 template trials)",
        "field": "bor_bin",
        "issue_type": "unresolved_derivation",
        "current_behavior":
            "NA in harmonized output; row added to flagged_for_review.csv per "
            "policy. NOT derived because rule isn't pinned down.",
        "candidate_source_files": "DERIVED from clinical_benefit.binary + pfs_time",
        "candidate_source_columns": "clinical_benefit.binary, pfs_time",
        "evidence_summary":
            "Across 9 template trials, clinical_benefit.binary=SD splits 99/178 between "
            "bor_bin=0/1 (clearly not a function of clinical_benefit.binary alone). Mean "
            "pfs_time differs: 83d for bor_bin=0, 266d for bor_bin=1. "
            "Hypothesis `1 iff R OR (SD AND pfs_time>=183)` matches 86% of "
            "CIMAC-s1400i rows and 78% of EAY131_Z1D — close to the standard "
            "'clinical benefit rate' definition but not perfect.",
        "human_question":
            "Is bor_bin the standard clinical-benefit indicator "
            "(CR/PR plus SD lasting >=6 months), and what is the exact PFS "
            "threshold (days) for each trial?",
        "recommended_next_action":
            "Provide the operational definition from the original analysis "
            "plan (or pointer to the statistician). Once confirmed, add a "
            "single derivation block in harmonization_config.yaml "
            "(bor_bin_rule: {threshold_days: N, criteria: ...}) and the "
            "extractor helper will emit it with high confidence.",
    },
    {
        "priority": "P3",
        "trial": "ALL (9 template trials)",
        "field": "pfs_bin",
        "issue_type": "unresolved_derivation",
        "current_behavior":
            "NA in harmonized output; flagged for every row.",
        "candidate_source_files": "DERIVED from pfs_stat + pfs_time",
        "candidate_source_columns": "pfs_stat, pfs_time",
        "evidence_summary":
            "Template pfs_bin does NOT mirror pfs_stat (counter-examples in every "
            "trial). Hypothesis `1 iff pfs_time>=183 OR pfs_stat=0` matches "
            "81% on CIMAC-s1400i and 81% on EAY131_Z1D — suggestive of a "
            "6-month PFS landmark indicator but not exact.",
        "human_question":
            "What is the canonical pfs_bin rule? Standard candidates: "
            "(a) 6-month PFS landmark, (b) 4-month PFS, (c) trial-specific.",
        "recommended_next_action":
            "Confirm rule + threshold; commit to harmonization_config.yaml.",
    },
    {
        "priority": "P3",
        "trial": "CIMAC-s1400i",
        "field": "age",
        "issue_type": "source_data_not_derivable",
        "current_behavior":
            "Emitted with confidence 0.55 (below 0.80 threshold) → NA in "
            "harmonized output; row flagged.",
        "candidate_source_files": "Clinical Dataset 2023_03_14.csv (age_num)",
        "candidate_source_columns": "age_num (integer, age at enrollment)",
        "evidence_summary":
            "Template age values are decimals (e.g., 50.5, 47.9, 79.3); source "
            "`age_num` is integer (enrollment age). Difference is sample-time "
            "offset, which requires per-sample collection date — NOT present "
            "in any S1400I source file.",
        "human_question":
            "Where is the per-sample collection date for S1400I stored? "
            "(External CIMAC sample manifest? Another file we missed?)",
        "recommended_next_action":
            "If sample collection dates can be supplied (CSV with cimac_part_id, "
            "Cimac.id, collection_date), the extractor will compute decimal "
            "age. Otherwise accept enrollment-age proxy with documented caveat.",
    },
    {
        "priority": "P2",
        "trial": "10013",
        "field": "Cimac.id",
        "issue_type": "cimac_id_absent_in_source",
        "current_behavior":
            "All 196 anchor rows emit Cimac.id=NA + flagged. P2 pass "
            "performed an exhaustive scan of every cell of every file in "
            "10013-clinical/ for strings starting with any known cimac_part_id "
            "(7-char prefix) followed by a sample-suffix: zero hits.",
        "candidate_source_files":
            "specimen_collection_2023-09-13.csv (cimac_part_id + M-codes only)",
        "candidate_source_columns":
            "M6 (sample type), M7 (visit), M2 (days), M4 (anatomic site) — no sample identifier",
        "evidence_summary":
            "Confirmed: no column in any 10013 file holds sample-level Cimac.id. "
            "External CIMAC manifest is the only way to populate this column.",
        "human_question":
            "Is there a CIMAC sample manifest for 10013 we can be pointed to? "
            "(Path / Google Drive / ShipRamp export.)",
        "recommended_next_action":
            "Place the manifest file under 10013-clinical/ and update YAML "
            "source mapping. Without it, harmonized rows ship with NA Cimac.id.",
    },
    {
        "priority": "P2",
        "trial": "14C0059G",
        "field": "Cimac.id",
        "issue_type": "cimac_id_absent_in_source",
        "current_behavior":
            "All 23 anchor rows emit Cimac.id=NA + flagged. P2 pass scanned "
            "all 26 files for any string starting with a known cimac_part_id "
            "(e.g., CA44FBW) followed by a sample suffix: zero hits.",
        "candidate_source_files":
            "research_sample_collection_apheresis.csv (cimac_part_id + Visit + Days only)",
        "candidate_source_columns": "(no sample-level id column)",
        "evidence_summary":
            "Confirmed: 14C0059G has no CIDC annotation file and no specimen-linkage "
            "table with Cimac.id. External manifest required.",
        "human_question":
            "Is there a CIMAC manifest or assay-shipping log for 14C0059G that "
            "maps (Patient, Visit) → Cimac.id?",
        "recommended_next_action":
            "Add the manifest to 14C0059G-clinical/ and configure as the "
            "source for Cimac.id in the YAML.",
    },
    {
        "priority": "P2",
        "trial": "14C0059G",
        "field": "age",
        "issue_type": "source_field_missing",
        "current_behavior":
            "Emitted with confidence 0.30 → NA + flagged for all rows.",
        "candidate_source_files":
            "patient_demographics_all.csv (8 cols, no Age column)",
        "candidate_source_columns": "(none)",
        "evidence_summary":
            "Source demographics file has Race, Gender, Ethnicity, ECOG cols "
            "but no Age column. enrollment.csv lacks age too.",
        "human_question":
            "Is there a separate age-at-enrollment file for 14C0059G? Or is "
            "age intentionally omitted (e.g., PHI redaction)?",
        "recommended_next_action":
            "If age intentionally redacted, document in the trial-level "
            "notes and lower the age threshold for this trial only. Otherwise "
            "obtain age data.",
    },
    {
        "priority": "P1",
        "trial": "10104",
        "field": "os_time / pfs_time",
        "issue_type": "source_column_choice",
        "current_behavior":
            "Currently picking the 'from PT_REG_DT_INT' columns; matches "
            "10% of template rows. Most values differ substantially.",
        "candidate_source_files":
            "10104_armaandb_response_pfsos_treatment_update.2023-04-04.csv, "
            "10104_armc_response_pfsos_treatment_update16mar2023.2023-04-04.csv",
        "candidate_source_columns":
            "Per file there are TWO sets of survival columns: "
            "(a) from PT_REG_DT_INT (registration date) and "
            "(b) from first_cycle_first_day. Template values likely use the "
            "first_cycle_first_day variant.",
        "evidence_summary":
            "Match rate 0.099 (os_time) / 0.113 (pfs_time). Same patient rows "
            "show source PT_REG_DT_INT values diverging from template by ~5-30 days.",
        "human_question":
            "Confirm template's 10104 os_time/pfs_time are anchored to "
            "first_cycle_first_day (not PT_REG_DT_INT). If yes, we just "
            "swap the column choice.",
        "recommended_next_action":
            "Update response_columns_aandb / response_columns_armc in YAML "
            "to use the 'first_cycle_first_day' columns; re-run pipeline.",
    },
    {
        "priority": "P1",
        "trial": "CIMAC-e4412",
        "field": "os_time / pfs_time",
        "issue_type": "unit_conversion_or_anchor",
        "current_behavior":
            "Multiplying weeks × 7 (os_wk → os_time days); 0% match.",
        "candidate_source_files": "baseline_outcomes.xlsx (Sheet1)",
        "candidate_source_columns":
            "os_wk, pfs_wk (weeks since enrollment), "
            "BRENTUXIMAB_STRT_fr_enrol / NIVOLUMAB_STRT_fr_enrol / "
            "LAST_PROT_TX_fr_enrol (week offsets to other events).",
        "evidence_summary":
            "Source os_wk first row = 1.56879 (weeks); × 7 = ~11 days. Template "
            "os_time for E4412 has ranges in hundreds of days. Suggests either "
            "(a) different anchor (e.g., from diagnosis rather than enrollment) "
            "or (b) a different column.",
        "human_question":
            "Is template E4412 os_time defined as weeks×7 from enrollment, or "
            "from a different anchor (e.g., diagnosis, treatment start)? "
            "Same for pfs_time.",
        "recommended_next_action":
            "Compare per-patient os_time template values to (os_wk × 7) + "
            "(LAST_PROT_TX_fr_enrol × 7) to identify the anchor. Adjust YAML.",
    },
    {
        "priority": "P1",
        "trial": "CIMAC-e4412",
        "field": "treatment",
        "issue_type": "value_map_incomplete",
        "current_behavior":
            "Mapping PROT_TX_ARM_ASS_TXT one-letter codes (E→BV+ipi, G→BV+nivo+ipi, "
            "Other→BV+nivo). Match 0.293.",
        "candidate_source_files":
            "baseline_outcomes.xlsx (PROT_TX_ARM_ASS_TXT), "
            "CIDC_Annotations_E4412_20230327.xlsx (arm codebook?)",
        "candidate_source_columns":
            "PROT_TX_ARM_ASS_TXT — values seen: E, G, plus possibly C/D/F. "
            "Codebook tab in adverse_events.xlsx / treatment.xlsx may list mapping.",
        "evidence_summary":
            "Template treatment values for E4412: BV+ipi (67), BV+nivo+ipi (52), "
            "BV+nivo (48) = 167. Our E→BV+ipi covers part of these but the "
            "other letters are not yet decoded.",
        "human_question":
            "Provide (or confirm in the codebook) the mapping for every "
            "PROT_TX_ARM_ASS_TXT letter code → treatment label.",
        "recommended_next_action":
            "Open the Codebook sheet of treatment.xlsx (12 rows) — the arm "
            "decoding is almost certainly there. Update YAML treatment_per_arm "
            "with the full mapping.",
    },
    {
        "priority": "P1",
        "trial": "CIMAC-gu16257",
        "field": "phase",
        "issue_type": "source_field_unknown",
        "current_behavior":
            "Emitted with confidence 0.30 → NA + flagged. Match 0.015.",
        "candidate_source_files":
            "data_dictionary.2023-01-19.xlsx, response.2023-01-04.csv (RESPTYPE), "
            "disease.2023-01-04.csv, treatment.2023-01-04.csv",
        "candidate_source_columns":
            "Unknown. Template phase Y=24 / N=169 / NaN=3 — a binary indicator "
            "(NOT phase I/II). Possibly tied to a treatment-completion flag or "
            "a sub-cohort.",
        "evidence_summary":
            "Template's 'phase' column for GU16-257 holds Y/N (not phase I/II). "
            "Source has 'CLCRFL' (clinical complete response flag) Y/N which "
            "has the right cardinality. Worth testing.",
        "human_question":
            "What does the GU16-257 template 'phase' Y/N actually encode? "
            "Is it CLCRFL or another response.csv flag?",
        "recommended_next_action":
            "Cross-tab template phase against response.csv columns (CLCRFL, "
            "CYSTSTAT, RESPTYPE) per cimac_part_id to identify the source. "
            "Then add a phase column in YAML.",
    },
    {
        "priority": "P1",
        "trial": "CIMAC-gu16257",
        "field": "clinical_benefit",
        "issue_type": "value_map_incomplete",
        "current_behavior":
            "Currently mapping source RESPTYPE R→Y, N→N, NE→NE; match 0.571.",
        "candidate_source_files":
            "response.2023-01-04.csv (RESPTYPE, CLCRFL, CYSTSTAT, RECCUR)",
        "candidate_source_columns":
            "Combinations of multiple response flags — RESPTYPE alone seems "
            "insufficient. CLCRFL (clinical complete response flag) may be the "
            "stronger predictor.",
        "evidence_summary":
            "Template GU16-257 clinical_benefit: Y=112, N=78, NE=6 (total 196). Source "
            "RESPTYPE alone gives ~57% match. Other response flags exist and "
            "may combine.",
        "human_question":
            "How is GU16-257 clinical_benefit Y/N/NE derived from response.csv? Single "
            "column? Composite of CLCRFL + RECCUR?",
        "recommended_next_action":
            "Compute combinations of (RESPTYPE, CLCRFL, RECCUR) per row and "
            "find the rule that reproduces template clinical_benefit. Likely a 2-line "
            "Python check on the response file.",
    },
    # BACCI checklist item removed — trial excluded from pipeline.
]


# ── Auto-derived items ───────────────────────────────────────────────────
def auto_low_match_items(val_summary: pd.DataFrame) -> list[dict]:
    """Pick (trial, column) cells below 0.95 match (excluding policy NAs)."""
    excluded = {"bor_bin", "pfs_bin", "age"}  # already covered by manual items
    sub = val_summary[
        (val_summary["match_rate"] < 0.95) & (~val_summary["column"].isin(excluded))
    ].copy()
    if sub.empty:
        return []
    # Already covered above by hand-authored entries for the named columns
    covered = {
        ("10104", "os_time"), ("10104", "pfs_time"),
        ("CIMAC-e4412", "os_time"), ("CIMAC-e4412", "pfs_time"),
        ("CIMAC-e4412", "treatment"),
        ("CIMAC-gu16257", "phase"), ("CIMAC-gu16257", "clinical_benefit"),
    }
    items = []
    for _, r in sub.iterrows():
        if (r["trial"], r["column"]) in covered:
            continue
        match = float(r["match_rate"])
        n_rows = int(r["n_rows"])
        priority = "P1" if match < 0.50 else ("P2" if match < 0.80 else "P3")
        items.append({
            "priority": priority,
            "trial": r["trial"],
            "field": r["column"],
            "issue_type": "template_match_low",
            "current_behavior": (
                f"Match rate {match:.3f} across {n_rows} rows "
                f"({int(match*n_rows)} match / {n_rows - int(match*n_rows)} mismatch)."
            ),
            "candidate_source_files": "(see provenance_long.csv for this (trial, field))",
            "candidate_source_columns": "(see provenance_long.csv)",
            "evidence_summary": (
                f"Validation: template_match_rate={match:.3f}. Investigate "
                f"specific rows via validation_report.csv filter "
                f"trial=={r['trial']!r} & column=={r['column']!r}."
            ),
            "human_question": (
                f"What source column or transformation should be used for "
                f"{r['trial']} {r['column']} to better match the template?"
            ),
            "recommended_next_action": (
                f"Inspect validation_report.csv for {r['trial']}/{r['column']}; "
                f"identify the divergence pattern; refine value_map or "
                f"column choice in harmonization_config.yaml; re-run pipeline."
            ),
        })
    return items


def auto_flagged_impact_items(flagged: pd.DataFrame, harmonized: pd.DataFrame) -> list[dict]:
    """High-impact (trial, field) flagged groups by n_rows."""
    if flagged.empty:
        return []
    g = flagged.groupby(["trial", "harmonized_field"]).size().reset_index(name="n_flagged")
    # Filter out groups already covered above and policy-driven NAs
    covered = {
        ("10013", "Cimac.id"), ("14C0059G", "Cimac.id"),
        ("CIMAC-s1400i", "age"), ("14C0059G", "age"),
        ("CIMAC-gu16257", "phase"), ("CIMAC-gu16257", "clinical_benefit"),
        ("CIMAC-e4412", "treatment"),
    }
    suppress_fields = {"bor_bin", "pfs_bin"}  # covered by manual cross-trial items
    items = []
    for _, r in g.sort_values("n_flagged", ascending=False).iterrows():
        key = (r["trial"], r["harmonized_field"])
        if key in covered or r["harmonized_field"] in suppress_fields:
            continue
        if r["n_flagged"] < 30:
            continue
        items.append({
            "priority": "P2" if r["n_flagged"] >= 100 else "P3",
            "trial": r["trial"],
            "field": r["harmonized_field"],
            "issue_type": "high_flag_volume",
            "current_behavior": f"{r['n_flagged']} rows flagged for review (NA in harmonized output).",
            "candidate_source_files": "(see flagged_for_review.csv source_files col)",
            "candidate_source_columns": "(see flagged_for_review.csv candidate_source_variables col)",
            "evidence_summary": (
                f"{r['n_flagged']} cells in {r['trial']} have confidence below "
                f"threshold for {r['harmonized_field']}."
            ),
            "human_question": (
                f"Is there a known authoritative source for "
                f"{r['trial']} {r['harmonized_field']} that the pipeline missed?"
            ),
            "recommended_next_action": (
                f"Filter flagged_for_review.csv to "
                f"trial=={r['trial']!r} & harmonized_field=={r['harmonized_field']!r}, "
                f"inspect notes / proposed_mapping; decide whether the field "
                f"is genuinely unrecoverable from source (then accept NA) or "
                f"the YAML config needs a new column / value_map."
            ),
        })
        if len(items) >= 8:
            break
    return items


SCHEMA = [
    "priority", "trial", "field", "issue_type", "n_rows_affected",
    "current_behavior", "candidate_source_files", "candidate_source_columns",
    "evidence_summary", "human_question", "recommended_next_action",
]


def assemble(val_summary: pd.DataFrame, flagged: pd.DataFrame, harmonized: pd.DataFrame) -> pd.DataFrame:
    rows = list(MANUAL_ITEMS)
    rows += auto_low_match_items(val_summary)
    rows += auto_flagged_impact_items(flagged, harmonized)

    # Attach n_rows_affected from harmonized + flagged where possible
    for r in rows:
        if "n_rows_affected" not in r:
            t = r.get("trial", "")
            f = r.get("field", "")
            if t == "ALL (9 template trials)":
                r["n_rows_affected"] = int(len(harmonized[harmonized["trial"].isin([
                    "CIMAC-9204", "CIMAC-10021", "10026", "10104", "ABTC1603",
                    "CIMAC-e4412", "EAY131_Z1D", "CIMAC-gu16257", "CIMAC-s1400i",
                ])]))
            elif t in harmonized["trial"].values:
                r["n_rows_affected"] = int((harmonized["trial"] == t).sum())
            else:
                r["n_rows_affected"] = ""

    df = pd.DataFrame(rows)
    # Sort: P1 first, then P2, P3
    df["_p"] = df["priority"].map({"P1": 1, "P2": 2, "P3": 3}).fillna(9)
    df = df.sort_values(["_p", "trial", "field"]).drop(columns=["_p"])
    return df[SCHEMA]


def write_markdown(df: pd.DataFrame, md_path: Path) -> None:
    lines = []
    lines.append("# Human-review checklist — CIMAC harmonization")
    lines.append("")
    lines.append("Generated from current `harmonization_outputs/` state. **Do not** "
                 "modify harmonized CSVs while addressing these items; instead "
                 "edit `scripts/config/harmonization_config.yaml` and re-run "
                 "the pipeline.")
    lines.append("")
    for prio in ("P1", "P2", "P3"):
        sub = df[df["priority"] == prio]
        if sub.empty:
            continue
        lines.append(f"## {prio} — {len(sub)} item{'s' if len(sub)!=1 else ''}")
        lines.append("")
        for i, r in sub.iterrows():
            title = f"{r['trial']} · `{r['field']}`"
            lines.append(f"### {title}")
            lines.append("")
            lines.append(f"- **Issue type:** {r['issue_type']}")
            if r.get("n_rows_affected"):
                lines.append(f"- **Rows affected:** {r['n_rows_affected']}")
            lines.append(f"- **Current behavior:** {r['current_behavior']}")
            lines.append(f"- **Candidate source files:** {r['candidate_source_files']}")
            lines.append(f"- **Candidate source columns:** {r['candidate_source_columns']}")
            lines.append(f"- **Evidence:** {r['evidence_summary']}")
            lines.append(f"- **Question for reviewer:** {r['human_question']}")
            lines.append(f"- **Recommended next action:** {r['recommended_next_action']}")
            lines.append("")
    md_path.write_text("\n".join(lines))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(OUTDIR))
    args = ap.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    outdir = Path(args.out)

    val_summary = pd.read_csv(outdir / "validation_summary.csv")
    flagged     = pd.read_csv(outdir / "flagged_for_review.csv")
    harmonized  = pd.read_csv(outdir / "harmonized_11trials.csv")

    df = assemble(val_summary, flagged, harmonized)

    csv_path = outdir / "review_priority_checklist.csv"
    df.to_csv(csv_path, index=False)
    LOG.info("Wrote %s (%d items)", csv_path, len(df))

    md_path = outdir / "review_priority_checklist.md"
    write_markdown(df, md_path)
    LOG.info("Wrote %s", md_path)

    # Brief printout
    print(f"\nChecklist items by priority:")
    print(df["priority"].value_counts().to_string())
    print("\nFirst 10 items:")
    print(df[["priority", "trial", "field", "issue_type", "n_rows_affected"]].head(10).to_string(index=False))


if __name__ == "__main__":
    main()
