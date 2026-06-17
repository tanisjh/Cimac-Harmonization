"""
extract_harmonized_clinical.py — Orchestrator.

Calls each registered per-trial extractor, concatenates the long-form Cell
stream, pivots to the wide 20-column template schema, applies per-field
confidence thresholds (cells below threshold → NA + flagged_for_review row),
reorders the 9-trial reproduction to match the original template row order,
and writes:

  harmonization_outputs/harmonized_9trials_reproduced.csv   # wide, template-ordered
  harmonization_outputs/harmonized_11trials.csv             # all included trials
  harmonization_outputs/provenance_long.csv                 # long with provenance
  harmonization_outputs/flagged_for_review.csv              # below-threshold cells
  harmonization_outputs/row_order_diagnostics.csv           # template-order audit
"""
from __future__ import annotations

import argparse
import importlib
import logging
import sys
from dataclasses import asdict
from pathlib import Path

import pandas as pd
import yaml

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "scripts"))

from lib.provenance import Cell, FlagRow

LOG = logging.getLogger("orchestrator")

# Final template schema (19 columns). BOR / BOR.binary were renamed to
# clinical_benefit / clinical_benefit.binary on 2026-05-20 per reviewer decision.
TEMPLATE_COLUMNS = [
    "cimac_part_id", "Cimac.id", "Collection_Event", "race", "sex", "age", "arm",
    "os_time", "os_stat", "pfs_time", "pfs_stat", "clinical_benefit", "treatment", "phase",
    "trial", "clinical_benefit.binary", "Collection_Event_alt", "pfs_bin", "bor_bin",
]

# Registry: trial_dir_name → module path.
#
# BACCI-clinical is intentionally NOT registered: it is not part of the CIMAC
# clinical-trial set. scripts/extractors/bacci.py is retained on disk for
# history but is inactive — re-register here only if BACCI is reintroduced.
EXTRACTORS = {
    "S1400I-clinical":     "extractors.s1400i",
    "EAY131-Z1D-clinical": "extractors.eay131_z1d",
    "ABTC1603-clinical":   "extractors.abtc1603",
    "10026-clinical":      "extractors.nci_10026",
    "GU16-257-clinical":   "extractors.gu16_257",
    "10104-clinical":      "extractors.nci_10104",
    "10021-clinical":      "extractors.nci_10021",
    "9204-clinical":       "extractors.nci_9204",
    "E4412-clinical":      "extractors.e4412",
    # New trials (no template anchors; extractors build their own row structure)
    "10013-clinical":      "extractors.nci_10013",
    "14C0059G-clinical":   "extractors.nih_14c0059g",
}

# Stable row-order key used to align the 9-trial reproduction to the original
# template. Unique in both files (verified: 1781 rows, 1781 unique keys).
ROW_ORDER_KEY_COLS = ["trial", "cimac_part_id", "Cimac.id", "Collection_Event"]


def load_config(path: Path) -> dict:
    with path.open() as f:
        return yaml.safe_load(f)


def load_template(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path, index_col=0)
    df = df.reset_index(drop=True)
    return df


def run_extractor(module_name: str, project_root: Path, anchor_df: pd.DataFrame,
                  trial_cfg: dict, value_norms: dict, derived_rules: dict) -> list[Cell]:
    mod = importlib.import_module(module_name)
    cls = getattr(mod, "Extractor")
    inst = cls(project_root=project_root, anchor_df=anchor_df, trial_config=trial_cfg,
               value_norms=value_norms, derived_rules=derived_rules)
    cells: list[Cell] = list(inst.extract())
    LOG.info("  %s emitted %d cells", module_name, len(cells))
    return cells


def threshold_for(field: str, thresholds_cfg: dict) -> float:
    return float(thresholds_cfg.get("per_field", {}).get(field, thresholds_cfg.get("default", 0.7)))


def apply_gold_clinical_benefit(df: pd.DataFrame, gold_cb_cfg: dict) -> tuple[pd.DataFrame, list[dict]]:
    """GOLD-ONLY: derive clinical_benefit / clinical_benefit.binary from a PFS
    landmark for configured trials (e.g. ABTC1603, which has no BOR/response
    source column).

    Rule (Dr. Ye final guidance, 2026-06-17), regardless of death reason:
        pfs_time >= landmark_days -> benefit values
        pfs_time <  landmark_days -> no-benefit values
        pfs_time missing/NA       -> left unchanged
    pfs_time / pfs_stat / pfs_bin / bor_bin are NOT touched. This is applied ONLY
    to the gold deliverable frames — never to the template-reproduction QC
    artifact, provenance, or the extractor output — so template fidelity and the
    validation comparison are unaffected. Returns (modified_df, audit_records).
    """
    if not gold_cb_cfg:
        return df, []
    df = df.copy()
    records: list[dict] = []
    pfs_all = pd.to_numeric(df["pfs_time"], errors="coerce")
    for trial_name, spec in gold_cb_cfg.items():
        spec = spec or {}
        landmark = float(spec.get("landmark_days", 120))
        ben = spec.get("benefit", {}) or {}
        no_ben = spec.get("no_benefit", {}) or {}
        trial_mask = df["trial"].astype(str) == str(trial_name)
        if not trial_mask.any():
            continue
        ben_mask = trial_mask & (pfs_all >= landmark)        # NaN -> False
        noben_mask = trial_mask & (pfs_all < landmark)       # NaN -> False
        na_mask = trial_mask & pfs_all.isna()
        for fld, val in ben.items():
            df.loc[ben_mask, fld] = val
        for fld, val in no_ben.items():
            df.loc[noben_mask, fld] = val
        records.append({
            "trial": str(trial_name),
            "rule": (f"pfs_time>={landmark:g} -> {ben}; "
                     f"pfs_time<{landmark:g} -> {no_ben}; pfs_time NA -> unchanged"),
            "n_benefit": int(ben_mask.sum()),
            "n_no_benefit": int(noben_mask.sum()),
            "n_unclassified_pfs_na": int(na_mask.sum()),
            "applied_to": "harmonized_9trials_gold.csv; harmonized_11trials.csv",
            "not_applied_to": "harmonized_9trials_reproduced.csv; provenance_long.csv",
            "reason": spec.get("reason", ""),
        })
    return df, records


def pivot_cells_to_wide(cells: list[Cell], thresholds_cfg: dict) -> tuple[pd.DataFrame, list[FlagRow]]:
    """
    Pivot long Cell stream to wide template-shaped DataFrame.
    For each (trial, cimac_part_id, Cimac.id, Collection_Event, harmonized_field):
      - if multiple Cells, take the one with highest confidence
      - if confidence < threshold, write NA and emit a FlagRow
    """
    rows: dict[tuple, dict] = {}
    best_by_key: dict[tuple, Cell] = {}
    for c in cells:
        key = (c.trial, c.cimac_part_id, c.Cimac_id, c.Collection_Event, c.harmonized_field)
        if key not in best_by_key or c.confidence > best_by_key[key].confidence:
            best_by_key[key] = c

    flags: list[FlagRow] = []
    for key, c in best_by_key.items():
        anchor = (c.trial, c.cimac_part_id, c.Cimac_id, c.Collection_Event)
        if anchor not in rows:
            rows[anchor] = {
                "cimac_part_id": c.cimac_part_id,
                "Cimac.id": c.Cimac_id,
                "Collection_Event": c.Collection_Event,
                "trial": c.trial,
            }
        thr = threshold_for(c.harmonized_field, thresholds_cfg)
        if c.confidence + 1e-9 >= thr and c.value is not None:
            rows[anchor][c.harmonized_field] = c.value
        else:
            rows[anchor].setdefault(c.harmonized_field, None)
            flags.append(FlagRow(
                trial=c.trial,
                cimac_part_id=c.cimac_part_id,
                Cimac_id=c.Cimac_id,
                Collection_Event=c.Collection_Event,
                harmonized_field=c.harmonized_field,
                source_files=c.source_file,
                candidate_source_variables=c.source_column,
                observed_source_values=c.notes,
                proposed_mapping=str(c.value) if c.value is not None else "",
                confidence_score=c.confidence,
                reason_low_confidence=(
                    "confidence_below_threshold"
                    if c.value is not None else "value_NA_at_extraction"
                ) + f" (threshold={thr:.2f})",
                question_for_reviewer=(
                    f"Is the proposed mapping for {c.harmonized_field} ({c.value!r}) correct given "
                    f"source={c.source_file}:{c.source_column}? extraction_method={c.extraction_method}"
                ),
            ))

    wide = pd.DataFrame(list(rows.values()))
    # Ensure all template columns exist; fill missing with NaN
    for col in TEMPLATE_COLUMNS:
        if col not in wide.columns:
            wide[col] = pd.NA
    wide = wide[TEMPLATE_COLUMNS]
    return wide, flags


def _row_key(df: pd.DataFrame, key_cols: list[str]) -> pd.Series:
    return df[key_cols].astype(str).agg("||".join, axis=1)


def align_to_template_order(reproduced: pd.DataFrame, template: pd.DataFrame, key_cols: list[str]) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Reorder `reproduced` so its rows align 1:1 with `template` by `key_cols`.

    Emits a diagnostics DataFrame with columns
        issue_type, trial, cimac_part_id, Cimac.id, Collection_Event, note
    covering:
      - in_template_not_in_reproduced
      - in_reproduced_not_in_template
      - duplicate_key_in_template
      - duplicate_key_in_reproduced
      - summary (ordered_match_template / row_count)

    The first 4 issue types should be empty for a healthy reproduction.
    """
    tmpl_keys = _row_key(template, key_cols)
    rep_keys  = _row_key(reproduced, key_cols)

    tmpl_set = set(tmpl_keys)
    rep_set  = set(rep_keys)
    missing_in_rep   = [k for k in tmpl_keys if k not in rep_set]
    extra_in_rep     = [k for k in rep_keys  if k not in tmpl_set]
    dup_in_template  = tmpl_keys[tmpl_keys.duplicated(keep=False)].tolist()
    dup_in_reproduced = rep_keys[rep_keys.duplicated(keep=False)].tolist()

    # Sort reproduced by template position. Unmatched rows (extra_in_rep) get
    # NaN order and are placed at the end; for a healthy run there are none.
    order_map = {k: i for i, k in enumerate(tmpl_keys)}
    reproduced = reproduced.copy()
    reproduced["_template_order"] = rep_keys.map(order_map)
    reproduced = (reproduced
                  .sort_values("_template_order", kind="mergesort", na_position="last")
                  .drop(columns=["_template_order"])
                  .reset_index(drop=True))

    # Verify alignment after sorting (ignoring any extras at the tail).
    rep_keys_sorted = _row_key(reproduced, key_cols)
    n_aligned = min(len(tmpl_keys), len(rep_keys_sorted))
    ordered_match = bool((tmpl_keys.values[:n_aligned] == rep_keys_sorted.values[:n_aligned]).all())

    rows: list[dict] = []
    def _add(issue: str, key: str, note: str = ""):
        parts = key.split("||")
        rec = {"issue_type": issue, "note": note}
        for i, c in enumerate(key_cols):
            rec[c] = parts[i] if i < len(parts) else ""
        rows.append(rec)

    for k in missing_in_rep:    _add("in_template_not_in_reproduced", k)
    for k in extra_in_rep:      _add("in_reproduced_not_in_template", k)
    for k in dup_in_template:   _add("duplicate_key_in_template", k)
    for k in dup_in_reproduced: _add("duplicate_key_in_reproduced", k)
    _add("summary", "||".join([""] * len(key_cols)),
         f"key_cols={key_cols}; template_rows={len(template)}; "
         f"reproduced_rows={len(reproduced)}; "
         f"ordered_match_after_sort={ordered_match}; "
         f"missing={len(missing_in_rep)}; extra={len(extra_in_rep)}; "
         f"dup_template={len(dup_in_template)}; dup_reproduced={len(dup_in_reproduced)}")

    LOG.info("Row-order audit: missing=%d extra=%d dup_template=%d dup_reproduced=%d ordered_match=%s",
             len(missing_in_rep), len(extra_in_rep), len(dup_in_template),
             len(dup_in_reproduced), ordered_match)

    cols = ["issue_type", *key_cols, "note"]
    return reproduced, pd.DataFrame(rows, columns=cols)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--template", default=str(PROJECT_ROOT / "cross_trial_analysis_egk_april30_meta_9trials.csv"))
    ap.add_argument("--config",   default=str(PROJECT_ROOT / "scripts" / "config" / "harmonization_config.yaml"))
    ap.add_argument("--out",      default=str(PROJECT_ROOT / "harmonization_outputs"))
    ap.add_argument("--trials",   default=None, help="comma-separated trial_dir_name filter (default: all registered)")
    ap.add_argument("-v", "--verbose", action="store_true")
    args = ap.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )

    template = load_template(Path(args.template))
    cfg = load_config(Path(args.config))
    outdir = Path(args.out)
    outdir.mkdir(parents=True, exist_ok=True)

    dir_to_trial_name = cfg.get("trial_dir_to_name", {})
    value_norms       = cfg.get("value_normalizations", {})
    trials_cfg        = cfg.get("trials", {})
    thresholds_cfg    = cfg.get("confidence_thresholds", {})
    derived_rules     = cfg.get("derived_rules", {})
    gold_cb_cfg       = cfg.get("gold_clinical_benefit_from_pfs", {}) or {}

    # Participant-level exclusions (screen failures, clinical team 2026-06).
    # excluded_set: {(trial, cimac_part_id)}; excluded_meta: per-trial reason.
    # These are dropped from the gold deliverables (9-trial gold + 11-trial)
    # but RETAINED in the template-reproduction QC artifact and provenance.
    excluded_cfg = cfg.get("excluded_participants", {}) or {}
    excluded_set: set[tuple[str, str]] = set()
    excluded_meta: dict[str, str] = {}
    for trial_name, spec in excluded_cfg.items():
        reason = (spec or {}).get("reason", "")
        excluded_meta[str(trial_name)] = reason
        for pid in (spec or {}).get("cimac_part_ids", []) or []:
            excluded_set.add((str(trial_name), str(pid)))
    if excluded_set:
        LOG.info("Loaded %d participant-level exclusions across %d trials",
                 len(excluded_set), len(excluded_cfg))

    selected = args.trials.split(",") if args.trials else list(EXTRACTORS.keys())
    all_cells: list[Cell] = []
    for tdir in selected:
        if tdir not in EXTRACTORS:
            LOG.warning("No extractor registered for %s — skipping", tdir)
            continue
        tname = dir_to_trial_name.get(tdir)
        if tname is None:
            LOG.warning("trial_dir %s not in trial_dir_to_name — skipping", tdir)
            continue
        anchor_rows = template[template["trial"] == tname].reset_index(drop=True)
        LOG.info("Trial %s (%s): %d anchor rows", tdir, tname, len(anchor_rows))
        # NOTE: anchor_rows may be empty for new trials (10013, 14C0059G);
        # those extractors construct their own anchors from source files.
        trial_cfg = trials_cfg.get(tdir, {})
        cells = run_extractor(EXTRACTORS[tdir], PROJECT_ROOT, anchor_rows, trial_cfg,
                              value_norms, derived_rules)
        all_cells.extend(cells)

    LOG.info("Total cells: %d", len(all_cells))
    wide, flags = pivot_cells_to_wide(all_cells, thresholds_cfg)

    # Write outputs. Three harmonized CSVs:
    #  - harmonized_9trials_reproduced.csv: the 9 template trials, reordered to
    #    match Edgar's original template row-by-row. HISTORICAL / TEMPLATE-
    #    REPRODUCTION QC ARTIFACT — retains the screen-failure ghost rows so it
    #    still byte-aligns to the 1,781-row template. Not the gold deliverable.
    #  - harmonized_9trials_gold.csv:        the corrected gold 9-trial output —
    #    the QC frame minus the confirmed screen-failure participants.
    #  - harmonized_11trials.csv:            the corrected 11-trial deliverable
    #    (9 template trials + 2 new), minus the screen-failure participants.
    template_trial_names = {
        "CIMAC-9204", "CIMAC-10021", "10026", "10104", "ABTC1603",
        "CIMAC-e4412", "EAY131_Z1D", "CIMAC-gu16257", "CIMAC-s1400i",
    }
    wide_9 = wide[wide["trial"].isin(template_trial_names)].reset_index(drop=True)

    # Reorder wide_9 to match the template's row order, write ordering diagnostics.
    # (Computed on the full QC frame so row-order fidelity to the template holds.)
    wide_9, diagnostics = align_to_template_order(wide_9, template, ROW_ORDER_KEY_COLS)
    wide_9_path = outdir / "harmonized_9trials_reproduced.csv"
    wide_9.to_csv(wide_9_path, index=False)
    LOG.info("Wrote %s (QC artifact: %d rows, %d cols, aligned to template order)",
             wide_9_path, len(wide_9), len(wide_9.columns))

    diag_path = outdir / "row_order_diagnostics.csv"
    diagnostics.to_csv(diag_path, index=False)
    LOG.info("Wrote %s (%d diagnostic rows)", diag_path, len(diagnostics))

    # Participant-level exclusion mask (gold deliverables only).
    def _is_excluded(df: pd.DataFrame) -> pd.Series:
        keys = list(zip(df["trial"].astype(str), df["cimac_part_id"].astype(str)))
        return pd.Series([k in excluded_set for k in keys], index=df.index)

    # Corrected gold 9-trial: QC frame minus excluded participants (order preserved).
    gold9_mask = _is_excluded(wide_9)
    wide_9_gold = wide_9[~gold9_mask].reset_index(drop=True)
    # GOLD-ONLY: derive clinical_benefit from the 4-month PFS cutoff (Dr. Ye,
    # 2026-06-17). Not applied to the reproduced QC artifact above.
    wide_9_gold, _ = apply_gold_clinical_benefit(wide_9_gold, gold_cb_cfg)
    wide_9_gold_path = outdir / "harmonized_9trials_gold.csv"
    wide_9_gold.to_csv(wide_9_gold_path, index=False)
    LOG.info("Wrote %s (gold 9-trial: %d rows; excluded %d screen-failure rows)",
             wide_9_gold_path, len(wide_9_gold), int(gold9_mask.sum()))

    # Corrected 11-trial deliverable: full frame minus excluded participants.
    full_mask = _is_excluded(wide)
    wide_11 = wide[~full_mask].reset_index(drop=True)
    # GOLD-ONLY: derive clinical_benefit from the 4-month PFS cutoff (Dr. Ye,
    # 2026-06-17). Same rule as the gold 9-trial frame above.
    wide_11, gold_cb_records = apply_gold_clinical_benefit(wide_11, gold_cb_cfg)
    wide_path = outdir / "harmonized_11trials.csv"
    wide_11.to_csv(wide_path, index=False)
    LOG.info("Wrote %s (deliverable: %d rows, %d cols; excluded %d screen-failure rows)",
             wide_path, len(wide_11), len(wide_11.columns), int(full_mask.sum()))

    # Provenance: retains ALL rows including excluded ghosts (full audit trail).
    prov_path = outdir / "provenance_long.csv"
    pd.DataFrame([c.as_record() for c in all_cells]).to_csv(prov_path, index=False)
    LOG.info("Wrote %s (%d cells; excluded rows retained for audit)", prov_path, len(all_cells))

    # flagged_for_review.csv is gold/deliverable-facing: drop flags for excluded
    # participants (those rows are now resolved by exclusion, not open follow-up
    # items). Also drop flags for (trial, field) pairs now resolved by the
    # gold-only clinical-benefit derivation (e.g. ABTC1603 clinical_benefit is no
    # longer "missing in source" — it is derived from the 4-month PFS cutoff).
    # Auditability is preserved via provenance_long + excluded_participants +
    # gold_clinical_benefit_derivation.csv.
    gold_cb_resolved: set[tuple[str, str]] = set()
    for trial_name, spec in gold_cb_cfg.items():
        spec = spec or {}
        for fld in {*(spec.get("benefit", {}) or {}), *(spec.get("no_benefit", {}) or {})}:
            gold_cb_resolved.add((str(trial_name), str(fld)))
    flags_kept = [
        f for f in flags
        if (str(f.trial), str(f.cimac_part_id)) not in excluded_set
        and (str(f.trial), str(f.harmonized_field)) not in gold_cb_resolved
    ]
    n_flags_dropped = len(flags) - len(flags_kept)
    flag_path = outdir / "flagged_for_review.csv"
    pd.DataFrame([f.as_record() for f in flags_kept]).to_csv(flag_path, index=False)
    LOG.info("Wrote %s (%d flagged cells; dropped %d resolved screen-failure flags)",
             flag_path, len(flags_kept), n_flags_dropped)

    # Audit artifact documenting the exclusions and where they were applied.
    excl_records = []
    excluded_from = "harmonized_9trials_gold.csv; harmonized_11trials.csv"
    retained_in = "harmonized_9trials_reproduced.csv; provenance_long.csv"
    for trial_name, pid in sorted(excluded_set):
        excl_records.append({
            "trial": trial_name,
            "cimac_part_id": pid,
            "reason": excluded_meta.get(trial_name, ""),
            "excluded_from": excluded_from,
            "retained_in": retained_in,
        })
    excl_path = outdir / "excluded_participants.csv"
    pd.DataFrame(excl_records, columns=[
        "trial", "cimac_part_id", "reason", "excluded_from", "retained_in",
    ]).to_csv(excl_path, index=False)
    LOG.info("Wrote %s (%d excluded participants)", excl_path, len(excl_records))

    # Audit artifact for the gold-only clinical-benefit derivation (4-month PFS
    # cutoff). Documents the rule and affected counts; mirrors the role of
    # excluded_participants.csv for the screen-failure exclusions.
    gold_cb_path = outdir / "gold_clinical_benefit_derivation.csv"
    pd.DataFrame(gold_cb_records, columns=[
        "trial", "rule", "n_benefit", "n_no_benefit", "n_unclassified_pfs_na",
        "applied_to", "not_applied_to", "reason",
    ]).to_csv(gold_cb_path, index=False)
    LOG.info("Wrote %s (%d gold clinical-benefit derivation rules)",
             gold_cb_path, len(gold_cb_records))


if __name__ == "__main__":
    main()
