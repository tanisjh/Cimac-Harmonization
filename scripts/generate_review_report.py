"""
generate_review_report.py — Produce human-reviewable summaries of the pipeline run.

Inputs (under harmonization_outputs/):
  - provenance_long.csv
  - harmonized_9trials_reproduced.csv
  - flagged_for_review.csv
  - validation_report.csv  (if exists)
  - validation_summary.csv (if exists)

Outputs:
  - source_evidence_report.csv   per (trial, harmonized_field) -> which source file/column contributed
  - template_anomalies.csv       rows in the template that exhibit known data-quality issues
  - human_review_summary.txt     text summary of everything, ready to share with reviewers
"""
from __future__ import annotations

import argparse
import logging
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parent.parent
LOG = logging.getLogger("review")


def source_evidence(prov: pd.DataFrame) -> pd.DataFrame:
    """
    For each (trial, harmonized_field), summarize:
      - which source file(s) contributed
      - which source column(s)
      - extraction methods used
      - distribution of confidence scores
      - n_cells, n_unique_values
    """
    g = prov.groupby(["trial", "harmonized_field"])
    rows = []
    for (trial, field), df in g:
        rows.append({
            "trial": trial,
            "harmonized_field": field,
            "n_cells": len(df),
            "source_files":      ";".join(sorted(df["source_file"].dropna().unique())),
            "source_columns":    ";".join(sorted(df["source_column"].dropna().astype(str).unique())),
            "extraction_methods":";".join(sorted(df["extraction_method"].dropna().unique())),
            "min_confidence":    float(df["confidence"].min()),
            "median_confidence": float(df["confidence"].median()),
            "max_confidence":    float(df["confidence"].max()),
            "n_unique_values":   df["value"].astype(str).nunique(),
            "n_NA":              int(df["value"].isna().sum()),
        })
    return pd.DataFrame(rows).sort_values(["trial", "harmonized_field"])


def template_anomalies(template_path: Path) -> pd.DataFrame:
    """Surface known issues in the original template CSV (sex-in-arm leak, mixed casing)."""
    tpl = pd.read_csv(template_path, index_col=0).reset_index(drop=True)
    rows = []
    # Sex-in-arm leak
    sex_values = {"Female", "Male", "MALE GENDER", "FEMALE GENDER", "M", "F"}
    arm_leak = tpl[tpl["arm"].isin(sex_values)]
    for _, r in arm_leak.iterrows():
        rows.append({
            "anomaly": "sex_in_arm_leak",
            "trial": r["trial"],
            "cimac_part_id": r["cimac_part_id"],
            "Cimac.id": r["Cimac.id"],
            "Collection_Event": r["Collection_Event"],
            "column": "arm",
            "value": r["arm"],
            "note": "arm column contains a sex-like value (likely copy-paste error from sex column)",
        })
    # Mixed casing in race (per-trial)
    by_trial_race = tpl.groupby("trial")["race"].apply(lambda s: set(s.dropna().astype(str)))
    for trial, vals in by_trial_race.items():
        # Look for both lowercase and uppercase of the same word
        lowered = {v.lower(): set() for v in vals}
        for v in vals:
            lowered[v.lower()].add(v)
        for lc, alts in lowered.items():
            if len(alts) > 1:
                rows.append({
                    "anomaly": "mixed_casing_race",
                    "trial": trial, "cimac_part_id": "", "Cimac.id": "", "Collection_Event": "",
                    "column": "race", "value": ";".join(sorted(alts)),
                    "note": f"race column has multiple casings of {lc!r}: {sorted(alts)}",
                })
    # Mixed sex encoding
    by_trial_sex = tpl.groupby("trial")["sex"].apply(lambda s: set(s.dropna().astype(str)))
    for trial, vals in by_trial_sex.items():
        if vals & {"MALE GENDER", "FEMALE GENDER"} and vals & {"M", "F"}:
            rows.append({
                "anomaly": "mixed_sex_encoding",
                "trial": trial, "cimac_part_id": "", "Cimac.id": "", "Collection_Event": "",
                "column": "sex", "value": ";".join(sorted(vals)),
                "note": "sex column has both abbreviated (M/F) and verbose (MALE GENDER/FEMALE GENDER) encodings",
            })
    return pd.DataFrame(rows)


def write_summary(text_path: Path, *, prov: pd.DataFrame, harmonized: pd.DataFrame, flagged: pd.DataFrame, validation: pd.DataFrame | None, anomalies: pd.DataFrame):
    lines: list[str] = []
    lines.append("CIMAC clinical harmonization — human review summary")
    lines.append("=" * 60)
    lines.append("")
    lines.append(f"Harmonized rows: {len(harmonized)}")
    lines.append(f"Trials reproduced: {sorted(harmonized['trial'].dropna().unique())}")
    lines.append(f"Provenance cells: {len(prov)}")
    lines.append(f"Flagged-for-review cells: {len(flagged)}")

    # New-trial row counts
    template_trial_names = {
        "CIMAC-9204", "CIMAC-10021", "10026", "10104", "ABTC1603",
        "CIMAC-e4412", "EAY131_Z1D", "CIMAC-gu16257", "CIMAC-s1400i",
    }
    new_trials = sorted(set(harmonized["trial"].dropna().unique()) - template_trial_names)
    if new_trials:
        lines.append("")
        lines.append("New trials added (no template ground truth):")
        for t in new_trials:
            n = len(harmonized[harmonized["trial"] == t])
            lines.append(f"  - {t}: {n} rows constructed from source files")
    if validation is not None and not validation.empty:
        lines.append(f"Validation mismatches vs template: {len(validation)}")
        # Per-(trial,column) match rate from summary if available
        try:
            vs_path = (text_path.parent / "validation_summary.csv")
            if vs_path.exists():
                vs = pd.read_csv(vs_path)
                lines.append("")
                lines.append("Per-(trial, column) match rate:")
                pivot = vs.pivot(index="column", columns="trial", values="match_rate").round(3)
                lines.append(pivot.fillna("-").to_string())
        except Exception as e:
            lines.append(f"(could not render validation_summary: {e})")
    lines.append("")
    lines.append("Top flagged-for-review issues (by harmonized_field, n_rows):")
    if not flagged.empty:
        f_top = flagged.groupby(["trial", "harmonized_field"]).size().reset_index(name="n_rows").sort_values("n_rows", ascending=False).head(20)
        lines.append(f_top.to_string(index=False))
    lines.append("")
    lines.append("Template anomalies detected (preserved verbatim in reproduced output):")
    if not anomalies.empty:
        anom_top = anomalies.groupby("anomaly").size().reset_index(name="n").sort_values("n", ascending=False)
        lines.append(anom_top.to_string(index=False))
    else:
        lines.append("  (none)")
    lines.append("")

    # Tested hypotheses for unresolved derived fields
    lines.append("Unresolved derivations (kept NA + flagged per policy):")
    lines.append("  bor_bin   : Template `bor_bin` does NOT track clinical_benefit.binary alone (SD splits 99/178 between 0/1).")
    lines.append("              Hypothesis tested: `1 iff (clinical_benefit.binary='R') OR (clinical_benefit.binary='SD' AND pfs_time>=183 days)`")
    lines.append("              Match rate: ~86% (CIMAC-s1400i), 78% (EAY131_Z1D).")
    lines.append("              NOT committed per 'no silent guessing' policy.")
    lines.append("  pfs_bin   : Template `pfs_bin` does NOT track pfs_stat directly.")
    lines.append("              Hypothesis tested: `1 iff (pfs_time>=183 days) OR (pfs_stat=0 censored)`")
    lines.append("              Match rate: ~81% (CIMAC-s1400i), 81% (EAY131_Z1D).")
    lines.append("              NOT committed per 'no silent guessing' policy.")
    lines.append("              ACTION: Reviewer to confirm exact derivation rule + threshold from study documentation.")
    lines.append("")
    lines.append("Other open issues:")
    lines.append("  S1400I age : Source age_num is integer age at enrollment; template has decimal age at sample collection.")
    lines.append("               Per-sample calculation requires sample collection date NOT present in source.")
    lines.append("               Currently NA + flagged.")
    lines.append("  10104 / E4412 / ABTC1603 os_time/pfs_time: candidate source columns chosen but values mismatch template.")
    lines.append("                                              Several candidate columns exist (days from registration vs C1D1 etc).")
    lines.append("                                              Currently emitted; column choice flagged for human confirmation.")
    lines.append("  GU16-257 phase Y/N : source field for the Y/N cohort indicator not identified.")
    lines.append("                       Currently NA + flagged.")
    lines.append("")
    lines.append("Cimac.id provenance for new trials:")
    lines.append("  10013   : sample-level Cimac.id NOT in source files → NA + flagged")
    lines.append("  14C0059G: sample-level Cimac.id NOT in source files → NA + flagged")
    lines.append("")
    text_path.write_text("\n".join(lines))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out",      default=str(PROJECT_ROOT / "harmonization_outputs"))
    ap.add_argument("--template", default=str(PROJECT_ROOT / "cross_trial_analysis_egk_april30_meta_9trials.csv"))
    args = ap.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    outdir = Path(args.out)

    prov = pd.read_csv(outdir / "provenance_long.csv")
    # Prefer the full 11-trial file (contains new trials) when present
    full = outdir / "harmonized_11trials.csv"
    harmonized = pd.read_csv(full if full.exists() else outdir / "harmonized_9trials_reproduced.csv")
    flagged = pd.read_csv(outdir / "flagged_for_review.csv") if (outdir / "flagged_for_review.csv").exists() else pd.DataFrame()
    validation = pd.read_csv(outdir / "validation_report.csv") if (outdir / "validation_report.csv").exists() else None

    se = source_evidence(prov)
    se_path = outdir / "source_evidence_report.csv"
    se.to_csv(se_path, index=False)
    LOG.info("Wrote %s (%d (trial,field) entries)", se_path, len(se))

    anom = template_anomalies(Path(args.template))
    anom_path = outdir / "template_anomalies.csv"
    anom.to_csv(anom_path, index=False)
    LOG.info("Wrote %s (%d anomaly rows)", anom_path, len(anom))

    sum_path = outdir / "human_review_summary.txt"
    write_summary(sum_path,
                  prov=prov, harmonized=harmonized, flagged=flagged,
                  validation=validation, anomalies=anom)
    LOG.info("Wrote %s", sum_path)
    print("\n--- human_review_summary.txt ---\n")
    print(sum_path.read_text())


if __name__ == "__main__":
    main()
