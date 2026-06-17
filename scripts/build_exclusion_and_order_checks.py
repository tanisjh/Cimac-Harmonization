"""
build_exclusion_and_order_checks.py — Post-run reproducibility checks.

Reads the freshly written harmonization_outputs/ and emits
    harmonization_outputs/exclusion_and_order_checks.txt

Verifies:
  * BACCI exclusion across regenerated artifacts (CSVs: row count;
    MD/CSV reports: text mentions, allowing only explicit exclusion notes).
  * 9-trial reproduction is row-aligned to the original template under the
    configured ROW_ORDER_KEY_COLS key (missing / extra / duplicate counts).
  * Final 11-trial output trial set + per-trial row counts.
  * harmonized_12trials.csv is absent.

This is a verification step only — it never edits harmonized data or any
report. Designed to be the wrapper's penultimate step (before
build_final_handoff.py, so the handoff report can list this file with a
real byte size).
"""
from __future__ import annotations

import argparse
import logging
import re
import sys
from datetime import datetime
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "scripts"))

# Reuse the same row-order key the orchestrator uses, so the two files
# stay in lock-step if the key is ever changed in one place.
from extract_harmonized_clinical import ROW_ORDER_KEY_COLS  # noqa: E402

LOG = logging.getLogger("exclusion_checks")

# A BACCI mention in a *report* (MD/CSV) is acceptable only if the line
# is an explicit exclusion / change-log note. We don't want to require
# zero mentions, because the handoff report intentionally records that
# BACCI was removed.
# 'exclu' covers exclude/excluded/exclusion/excluding; 'remov' covers
# removed/removal; 'intention' covers intentional/intentionally;
# 'deprecat' covers deprecate/deprecated.
_EXCLUSION_LINE_PATTERN = re.compile(
    r"(exclu|remov|intention|not part of the CIMAC|deprecat)",
    re.IGNORECASE,
)


def _count_bacci_rows(path: Path, col: str = "trial") -> int | None:
    if not path.exists():
        return None
    df = pd.read_csv(path, low_memory=False)
    if col not in df.columns:
        return -1
    return int((df[col].astype(str) == "BACCI").sum())


def _scan_text_for_bacci(path: Path) -> tuple[int, list[str]]:
    """Return (n_lines_mentioning_BACCI, list_of_non_exclusion_lines)."""
    if not path.exists():
        return 0, []
    lines = path.read_text().splitlines()
    mentions = [ln for ln in lines if "BACCI" in ln]
    suspicious = [ln for ln in mentions if not _EXCLUSION_LINE_PATTERN.search(ln)]
    return len(mentions), suspicious


def _row_key(df: pd.DataFrame, key_cols: list[str]) -> pd.Series:
    return df[key_cols].astype(str).agg("||".join, axis=1)


def build_report(outdir: Path, template_path: Path) -> str:
    full_path = outdir / "harmonized_11trials.csv"
    nine_path = outdir / "harmonized_9trials_reproduced.csv"
    twelve_path = outdir / "harmonized_12trials.csv"

    full = pd.read_csv(full_path)
    nine = pd.read_csv(nine_path)
    template = pd.read_csv(template_path, index_col=0).reset_index(drop=True)

    # Row-order alignment of the 9-trial reproduction vs the template.
    t_keys = _row_key(template, ROW_ORDER_KEY_COLS)
    r_keys = _row_key(nine, ROW_ORDER_KEY_COLS)
    t_set, r_set = set(t_keys), set(r_keys)
    missing_in_rep   = [k for k in t_keys if k not in r_set]
    extra_in_rep     = [k for k in r_keys if k not in t_set]
    dup_in_template  = t_keys[t_keys.duplicated(keep=False)].tolist()
    dup_in_rep       = r_keys[r_keys.duplicated(keep=False)].tolist()
    row_order_match  = (t_keys.values.tolist() == r_keys.values.tolist())

    # BACCI counts in row-oriented CSV artifacts.
    bacci_csv = {
        "harmonized_11trials.csv":      _count_bacci_rows(full_path),
        "provenance_long.csv":          _count_bacci_rows(outdir / "provenance_long.csv"),
        "flagged_for_review.csv":       _count_bacci_rows(outdir / "flagged_for_review.csv"),
        "validation_report.csv":        _count_bacci_rows(outdir / "validation_report.csv"),
        "review_priority_checklist.csv":_count_bacci_rows(outdir / "review_priority_checklist.csv"),
        "final_handoff_report.csv":     _count_bacci_rows(outdir / "final_handoff_report.csv"),
    }

    # BACCI mentions in text reports (any non-exclusion line is suspicious).
    md_targets = ["final_handoff_report.md", "review_priority_checklist.md",
                  "nonperfect_match_review.md", "human_review_summary.txt"]
    bacci_md: dict[str, tuple[int, list[str]]] = {}
    for name in md_targets:
        bacci_md[name] = _scan_text_for_bacci(outdir / name)

    trials = sorted(full["trial"].dropna().unique().tolist())

    lines: list[str] = []
    lines.append("CIMAC harmonization — post-run exclusion & row-order checks")
    lines.append(f"Generated: {datetime.now().isoformat(timespec='seconds')}")
    lines.append(f"Script: scripts/build_exclusion_and_order_checks.py")
    lines.append(f"Inputs: {outdir.resolve()}  vs  {template_path.resolve()}")
    lines.append("=" * 72)
    lines.append("")

    lines.append("[1] BACCI rows in final output (harmonized_11trials.csv)")
    lines.append(f"    BACCI rows : {bacci_csv['harmonized_11trials.csv']}    (expected: 0)")
    lines.append("")

    lines.append("[2] Final trial count")
    lines.append(f"    n_trials = {len(trials)}    (expected: 11)")
    lines.append("")

    lines.append("[3] Final trial list (alphabetical, with row counts)")
    for t in trials:
        lines.append(f"    - {t} ({int((full['trial']==t).sum())} rows)")
    lines.append("")

    lines.append("[4] Stale 12-trial output")
    lines.append(f"    harmonized_12trials.csv exists = {twelve_path.exists()}    (expected: False)")
    lines.append("")

    lines.append("[5] 9-trial reproduction row count")
    lines.append(f"    rows = {len(nine)}    (expected: 1781)")
    lines.append("")

    lines.append("[6] Template row count")
    lines.append(f"    rows = {len(template)}    (expected: 1781)")
    lines.append("")

    lines.append("[7] 9-trial row order matches template")
    lines.append(f"    matches = {row_order_match}    (expected: True)")
    lines.append(f"    key_cols = {ROW_ORDER_KEY_COLS}")
    lines.append("")

    lines.append("[8] Row-order key diagnostics")
    lines.append(f"    missing_template_keys_in_reproduced : {len(missing_in_rep)}    (expected: 0)")
    lines.append(f"    extra_reproduced_keys_not_in_template: {len(extra_in_rep)}    (expected: 0)")
    lines.append(f"    duplicate_keys_in_template          : {len(dup_in_template)}    (expected: 0)")
    lines.append(f"    duplicate_keys_in_reproduced        : {len(dup_in_rep)}    (expected: 0)")
    if missing_in_rep:
        lines.append(f"    first 5 missing_template_keys: {missing_in_rep[:5]}")
    if extra_in_rep:
        lines.append(f"    first 5 extra_reproduced_keys: {extra_in_rep[:5]}")
    lines.append("")

    lines.append("[9] BACCI rows in row-oriented artifacts (all expected: 0)")
    for fname, n in bacci_csv.items():
        if n is None:
            lines.append(f"    {fname:42s} (missing)")
        elif n == -1:
            lines.append(f"    {fname:42s} (no 'trial' column)")
        else:
            lines.append(f"    {fname:42s} {n}")
    lines.append("")

    lines.append("[10] BACCI textual mentions in report files")
    lines.append("     (mentions OK if line contains exclusion/removed/intentional/deprecated;")
    lines.append("      any 'non-exclusion' line is flagged for human review.)")
    all_clean = True
    for name, (n_total, suspicious) in bacci_md.items():
        ok = "OK" if not suspicious else f"FLAGGED ({len(suspicious)} non-exclusion line(s))"
        lines.append(f"     {name:42s} total_mentions={n_total:<3d} {ok}")
        if suspicious:
            all_clean = False
            for ln in suspicious[:5]:
                lines.append(f"        > {ln.strip()}")
    lines.append("")
    lines.append(f"     Overall textual-mentions verdict: {'OK' if all_clean else 'FLAGGED — see lines above'}")
    lines.append("")

    # ── Participant-level screen-failure exclusions (2026-06) ────────────────
    gold9_path = outdir / "harmonized_9trials_gold.csv"
    excl_path = outdir / "excluded_participants.csv"

    excl_failures: list[str] = []

    gold9 = pd.read_csv(gold9_path) if gold9_path.exists() else None
    excl_df = pd.read_csv(excl_path) if excl_path.exists() else None

    # Expected counts after exclusion of 11 participant rows: 10 screen-failure
    # rows (10026 ×7, ABTC1603 ×3) plus 14C0059G MISSING_0 (no assayed specimen,
    # CIDC confirmed 2026-06-15). The gold 9-trial count is unchanged because
    # 14C0059G is an extension trial absent from the 9-trial set.
    EXPECT_11_ROWS, EXPECT_GOLD9_ROWS = 1989, 1771
    EXPECT_EXCL_ROWS = 11

    excluded_pairs: set[tuple[str, str]] = set()
    if excl_df is not None:
        excluded_pairs = {(str(t), str(p))
                          for t, p in zip(excl_df["trial"], excl_df["cimac_part_id"])}

    def _pids_present(df: pd.DataFrame | None) -> set[str]:
        if df is None:
            return set()
        return set(df["cimac_part_id"].astype(str))

    full_pids = _pids_present(full)
    gold9_pids = _pids_present(gold9)
    nine_pids = _pids_present(nine)
    excl_pids = {p for (_t, p) in excluded_pairs}
    # The QC reproduction only contains the 9 template trials. Extension-trial
    # exclusions (e.g. 14C0059G) are legitimately absent from it, so the
    # "retained in QC reproduction" check applies only to template-trial PIDs.
    template_trials = set(nine["trial"].astype(str)) if nine is not None else set()
    qc_excl_pids = {p for (t, p) in excluded_pairs if t in template_trials}

    in_11   = sorted(p for p in excl_pids if p in full_pids)
    in_gold = sorted(p for p in excl_pids if p in gold9_pids)
    missing_from_qc = sorted(p for p in qc_excl_pids if p not in nine_pids)

    def _treatment_values(df: pd.DataFrame | None, trial: str) -> set[str]:
        if df is None or "treatment" not in df.columns:
            return set()
        sub = df[df["trial"].astype(str) == trial]
        return set(sub["treatment"].astype(str))

    ipi_aza_in_11   = "ipi_aza" in _treatment_values(full, "10026")
    ipi_aza_in_gold = "ipi_aza" in _treatment_values(gold9, "10026")
    ipi_dec_in_11   = "ipi_dec" in _treatment_values(full, "10026")
    ipi_dec_in_gold = "ipi_dec" in _treatment_values(gold9, "10026")

    lines.append("[11] Screen-failure participant exclusions (gold deliverables)")
    lines.append(f"    excluded_participants.csv present = {excl_df is not None}    "
                 f"(rows = {0 if excl_df is None else len(excl_df)}, expected: {EXPECT_EXCL_ROWS})")
    lines.append(f"    harmonized_11trials.csv rows = {len(full)}    (expected: {EXPECT_11_ROWS})")
    lines.append(f"    harmonized_9trials_gold.csv present = {gold9 is not None}, "
                 f"rows = {0 if gold9 is None else len(gold9)}    (expected: {EXPECT_GOLD9_ROWS})")
    lines.append(f"    excluded PIDs still in harmonized_11trials.csv  : {len(in_11)}    (expected: 0)")
    lines.append(f"    excluded PIDs still in harmonized_9trials_gold  : {len(in_gold)}    (expected: 0)")
    lines.append(f"    excluded PIDs retained in QC reproduction       : "
                 f"{len(qc_excl_pids) - len(missing_from_qc)}/{len(qc_excl_pids)}    "
                 f"(expected: {len(qc_excl_pids)}; template-trial exclusions only)")
    if in_11:   lines.append(f"    > present-in-11trials: {in_11}")
    if in_gold: lines.append(f"    > present-in-gold9:    {in_gold}")
    if missing_from_qc: lines.append(f"    > missing-from-QC:     {missing_from_qc}")
    lines.append("")

    lines.append("[12] 10026 treatment relabel (ipi_aza → ipi_dec)")
    lines.append(f"    ipi_aza in harmonized_11trials.csv  = {ipi_aza_in_11}    (expected: False)")
    lines.append(f"    ipi_aza in harmonized_9trials_gold  = {ipi_aza_in_gold}    (expected: False)")
    lines.append(f"    ipi_dec present (11trials / gold9)  = {ipi_dec_in_11} / {ipi_dec_in_gold}    (expected: True / True)")
    lines.append("")

    if excl_df is None:                 excl_failures.append("excluded_participants.csv missing")
    elif len(excl_df) != EXPECT_EXCL_ROWS: excl_failures.append(f"excluded_participants.csv has {len(excl_df)} rows (expected {EXPECT_EXCL_ROWS})")
    if gold9 is None:                   excl_failures.append("harmonized_9trials_gold.csv missing")
    elif len(gold9) != EXPECT_GOLD9_ROWS: excl_failures.append(f"gold 9-trial row count {len(gold9)} != {EXPECT_GOLD9_ROWS}")
    if len(full) != EXPECT_11_ROWS:     excl_failures.append(f"11-trial row count {len(full)} != {EXPECT_11_ROWS}")
    if in_11:                           excl_failures.append("excluded PIDs present in harmonized_11trials.csv")
    if in_gold:                         excl_failures.append("excluded PIDs present in harmonized_9trials_gold.csv")
    if missing_from_qc:                 excl_failures.append("excluded PIDs missing from QC reproduction")
    if ipi_aza_in_11 or ipi_aza_in_gold: excl_failures.append("ipi_aza still present in a gold output")
    if not (ipi_dec_in_11 and ipi_dec_in_gold): excl_failures.append("ipi_dec missing from a gold output")

    # Final pass/fail.
    failures = []
    if bacci_csv["harmonized_11trials.csv"] not in (0,):              failures.append("BACCI rows in harmonized_11trials.csv")
    if len(trials) != 11:                                              failures.append("trial count != 11")
    if twelve_path.exists():                                           failures.append("harmonized_12trials.csv still present")
    if len(nine) != 1781:                                              failures.append("9-trial reproduction row count != 1781")
    if len(template) != 1781:                                          failures.append("template row count != 1781")
    if not row_order_match:                                            failures.append("9-trial row order does not match template")
    if missing_in_rep or extra_in_rep or dup_in_template or dup_in_rep: failures.append("row-order key diagnostics non-zero")
    for fname, n in bacci_csv.items():
        if n not in (0, None, -1):
            failures.append(f"BACCI rows present in {fname}")
    if not all_clean:                                                  failures.append("non-exclusion BACCI mentions in reports")
    failures.extend(excl_failures)

    lines.append("=" * 72)
    if not failures:
        lines.append("VERDICT: PASS — all checks satisfied.")
    else:
        lines.append("VERDICT: FAIL — issues found:")
        for f in failures:
            lines.append(f"  - {f}")
    lines.append("")

    return "\n".join(lines)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out",      default=str(PROJECT_ROOT / "harmonization_outputs"))
    ap.add_argument("--template", default=str(PROJECT_ROOT / "cross_trial_analysis_egk_april30_meta_9trials.csv"))
    args = ap.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
    outdir = Path(args.out)
    text = build_report(outdir, Path(args.template))
    out_path = outdir / "exclusion_and_order_checks.txt"
    out_path.write_text(text)
    LOG.info("Wrote %s (%d bytes)", out_path, out_path.stat().st_size)

    # Echo the final VERDICT line for easy wrapper-log scanning.
    for ln in text.splitlines()[-6:]:
        print(ln)


if __name__ == "__main__":
    main()
