"""
validate_extractions.py — Compare reproduced harmonized output to the template.

Key:  (trial, cimac_part_id, Cimac.id, Collection_Event)
For each (key, column), compare template value vs reproduced value with
type-tolerant comparison (numeric ≈ numeric within tolerance; string
case-sensitive but trimmed; NaN equals NaN).

Outputs:
  harmonization_outputs/validation_report.csv  — cell-level mismatches
  harmonization_outputs/validation_summary.csv — per-(trial,column) match rate
"""
from __future__ import annotations

import argparse
import logging
from pathlib import Path

import numpy as np
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parent.parent
LOG = logging.getLogger("validate")

KEY_COLS = ["trial", "cimac_part_id", "Cimac.id", "Collection_Event"]
EXCLUDE_COMPARE = set(KEY_COLS)

# 2026-05-20: harmonized output columns BOR/BOR.binary were renamed to
# clinical_benefit/clinical_benefit.binary. Edgar's 9-trial template still uses
# the old names. Rename the template columns in-memory at read time so the rest
# of this script compares like-for-like against the pipeline output.
TEMPLATE_TO_PIPELINE = {
    "BOR":        "clinical_benefit",
    "BOR.binary": "clinical_benefit.binary",
}

# 2026-06: approved, source-backed value correction. The 10026 study regimen is
# ipilimumab + decitabine, so the pipeline emits treatment="ipi_dec". Edgar's
# historical template still carries the old "ipi_aza" label. Normalize the
# template's 10026 treatment value in-memory so this approved relabel is NOT
# reported as a mismatch in the historical QC comparison. Scoped to
# (trial=10026, column=treatment) only — no other trial/column is affected.
TEMPLATE_VALUE_NORMALIZATIONS = [
    # (trial, column, old_template_value, corrected_pipeline_value)
    ("10026", "treatment", "ipi_aza", "ipi_dec"),
]


def cell_equal(a, b, *, tol: float = 1e-3) -> bool:
    """Tolerant equality: NaN==NaN; numeric within tol; string compared trimmed."""
    a_na = a is None or (isinstance(a, float) and np.isnan(a)) or (isinstance(a, str) and a.strip().lower() in ("", "nan", "na", "<na>"))
    b_na = b is None or (isinstance(b, float) and np.isnan(b)) or (isinstance(b, str) and b.strip().lower() in ("", "nan", "na", "<na>"))
    if a_na and b_na:
        return True
    if a_na or b_na:
        return False
    try:
        return abs(float(a) - float(b)) <= tol
    except (TypeError, ValueError):
        pass
    return str(a).strip() == str(b).strip()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--template",   default=str(PROJECT_ROOT / "cross_trial_analysis_egk_april30_meta_9trials.csv"))
    ap.add_argument("--reproduced", default=str(PROJECT_ROOT / "harmonization_outputs" / "harmonized_9trials_reproduced.csv"))
    ap.add_argument("--out",        default=str(PROJECT_ROOT / "harmonization_outputs"))
    ap.add_argument("-v", "--verbose", action="store_true")
    args = ap.parse_args()

    logging.basicConfig(level=logging.DEBUG if args.verbose else logging.INFO,
                        format="%(asctime)s %(levelname)s %(message)s")

    tpl = pd.read_csv(args.template, index_col=0).reset_index(drop=True)
    tpl = tpl.rename(columns=TEMPLATE_TO_PIPELINE)
    # Apply approved, source-backed value corrections to the template in-memory
    # so the historical QC comparison treats the old label as equivalent to the
    # corrected pipeline value (e.g. 10026 treatment ipi_aza ≡ ipi_dec).
    for trial_name, column, old_val, new_val in TEMPLATE_VALUE_NORMALIZATIONS:
        if column in tpl.columns:
            mask = (tpl["trial"].astype(str) == trial_name) & (tpl[column].astype(str) == old_val)
            n = int(mask.sum())
            if n:
                tpl.loc[mask, column] = new_val
                LOG.info("Template value normalization: %s/%s %r→%r applied to %d rows",
                         trial_name, column, old_val, new_val, n)
    rep = pd.read_csv(args.reproduced)
    LOG.info("Template: %s rows. Reproduced: %s rows.", len(tpl), len(rep))

    # Restrict template to trials reproduced so far
    reproduced_trials = set(rep["trial"].dropna().unique())
    tpl_sub = tpl[tpl["trial"].isin(reproduced_trials)].copy()
    LOG.info("Comparing %d template rows for trials %s", len(tpl_sub), sorted(reproduced_trials))

    # Normalize key dtypes
    for df in (tpl_sub, rep):
        for c in KEY_COLS:
            df[c] = df[c].astype(str).str.strip()

    # Key match
    tpl_sub_key = tpl_sub.set_index(KEY_COLS, drop=False)
    rep_key     = rep.set_index(KEY_COLS, drop=False)

    only_in_tpl = tpl_sub_key.index.difference(rep_key.index)
    only_in_rep = rep_key.index.difference(tpl_sub_key.index)
    both        = tpl_sub_key.index.intersection(rep_key.index)
    LOG.info("Keys: %d in both, %d only in template, %d only in reproduced",
             len(both), len(only_in_tpl), len(only_in_rep))

    # Cell-level comparison
    compare_cols = [c for c in tpl.columns if c not in EXCLUDE_COMPARE and c in rep.columns]
    rows = []
    for key in both:
        t = tpl_sub_key.loc[key]
        r = rep_key.loc[key]
        # Handle duplicate keys (multi-row Series → DataFrame)
        if isinstance(t, pd.DataFrame):
            t = t.iloc[0]
        if isinstance(r, pd.DataFrame):
            r = r.iloc[0]
        for col in compare_cols:
            tv, rv = t.get(col), r.get(col)
            match = cell_equal(tv, rv)
            if not match:
                rows.append({
                    "trial": t["trial"], "cimac_part_id": t["cimac_part_id"],
                    "Cimac.id": t["Cimac.id"], "Collection_Event": t["Collection_Event"],
                    "column": col, "template_value": tv, "reproduced_value": rv,
                    "mismatch_kind": classify_mismatch(tv, rv),
                })

    rep_path = Path(args.out) / "validation_report.csv"
    pd.DataFrame(rows).to_csv(rep_path, index=False)
    LOG.info("Wrote %s (%d mismatches)", rep_path, len(rows))

    # Summary: per-(trial,column) match rate
    summary = []
    for trial in sorted(reproduced_trials):
        t_keys = [k for k in both if k[0] == trial]
        if not t_keys:
            continue
        for col in compare_cols:
            matches = 0
            misses = 0
            for key in t_keys:
                t = tpl_sub_key.loc[key]
                r = rep_key.loc[key]
                if isinstance(t, pd.DataFrame): t = t.iloc[0]
                if isinstance(r, pd.DataFrame): r = r.iloc[0]
                if cell_equal(t.get(col), r.get(col)):
                    matches += 1
                else:
                    misses += 1
            summary.append({
                "trial": trial, "column": col,
                "n_rows": matches + misses, "n_match": matches,
                "match_rate": (matches / (matches + misses)) if (matches + misses) else None,
            })
    sum_path = Path(args.out) / "validation_summary.csv"
    pd.DataFrame(summary).to_csv(sum_path, index=False)
    LOG.info("Wrote %s", sum_path)

    # Print a short tabular summary to stdout
    sdf = pd.DataFrame(summary)
    if not sdf.empty:
        print("\nPer-(trial, column) match rate:\n")
        pivot = sdf.pivot(index="column", columns="trial", values="match_rate").round(3)
        print(pivot.fillna("-").to_string())


def classify_mismatch(tv, rv):
    t_na = tv is None or (isinstance(tv, float) and np.isnan(tv)) or (isinstance(tv, str) and tv.strip().lower() in ("nan", "na"))
    r_na = rv is None or (isinstance(rv, float) and np.isnan(rv)) or (isinstance(rv, str) and rv.strip().lower() in ("nan", "na"))
    if t_na and not r_na:
        return "missing_in_template"
    if not t_na and r_na:
        return "missing_in_reproduced"
    try:
        if abs(float(tv) - float(rv)) > 1e-3:
            return "numeric_diff"
    except (TypeError, ValueError):
        pass
    if str(tv).strip().lower() == str(rv).strip().lower():
        return "case_diff"
    return "value_diff"


if __name__ == "__main__":
    main()
