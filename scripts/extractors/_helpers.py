"""Shared helpers used by per-trial extractors (kept small)."""
from __future__ import annotations

import re
import pandas as pd


def strip_norm(s):
    if s is None or (isinstance(s, float) and pd.isna(s)):
        return None
    return re.sub(r"\s+", " ", str(s)).strip()


def emit_anchor_cells(ext, anchor):
    """Yield the 4 anchor cells (cimac_part_id, Cimac.id, Collection_Event, trial)."""
    pid = str(anchor["cimac_part_id"])
    yield ext.cell(anchor, "cimac_part_id",    pid,                            1.0, "TEMPLATE_ANCHOR", "cimac_part_id", -1, "template_anchor_only")
    yield ext.cell(anchor, "Cimac.id",         str(anchor["Cimac.id"]),        1.0, "TEMPLATE_ANCHOR", "Cimac.id", -1, "template_anchor_only")
    yield ext.cell(anchor, "Collection_Event", str(anchor["Collection_Event"]),1.0, "TEMPLATE_ANCHOR", "Collection_Event", -1, "template_anchor_only")
    yield ext.cell(anchor, "trial",            ext.template_trial_name,        1.0, "CONFIG:trial_dir_to_name", "trial", -1, "trial_constant")


def emit_collection_event_alt(ext, anchor, ce_alt_map):
    raw_ce = str(anchor["Collection_Event"])
    val = (ce_alt_map or {}).get(raw_ce)
    yield ext.cell(
        anchor, "Collection_Event_alt", val,
        0.95 if val else 0.30,
        "CONFIG:collection_event_alt_map", "Collection_Event", -1,
        "value_map_collection_event",
        notes=f"raw_ce={raw_ce!r}" + (f" → {val!r}" if val else " (unmapped)"),
    )


_DERIVED_120D_STATUS = (
    "120-day landmark rule (template-supported derived rule; "
    "pending final clinical confirmation)"
)


def emit_unresolved_derived(ext, anchor, *, bor_value=None, pfs_stat_value=None,
                            pfs_time_value=None,
                            bor_binary_override=None):
    """Emit BOR.binary, bor_bin, pfs_bin for this anchor.

    - BOR.binary: derived from BOR via the global value_normalizations.BOR.binary
      mapping (CRm/CRi short codes are mapped to R per the 10026 Data Dictionary;
      see harmonization_config.yaml for the full mapping).
    - bor_bin: derived via the 120-day SD-landmark rule
      (scripts/lib/normalize.py::derive_bor_bin). Uses BOR.binary plus pfs_time
      when BOR.binary == 'SD'. Status: template-supported, pending final
      clinical confirmation.
    - pfs_bin: derived via the 120-day landmark rule
      (scripts/lib/normalize.py::derive_pfs_bin). Uses pfs_time plus pfs_stat.
      Same committed status.

    bor_binary_override: if a trial pre-computes BOR.binary via trial_constants
    (e.g., ABTC1603 emits BOR.binary='other' as a constant), pass it here so
    bor_bin sees the same value the wide pivot will land on.
    """
    if bor_binary_override is not None:
        bin_val = bor_binary_override
        # clinical_benefit.binary cell already emitted as trial_constant elsewhere
    else:
        bin_val, bin_conf, bin_note = ext.derive_BOR_binary(bor_value)
        if bin_val is not None:
            yield ext.cell(anchor, "clinical_benefit.binary", bin_val, bin_conf,
                           "DERIVED:BOR", "BOR", -1, "derived_bor_binary", notes=bin_note)
        else:
            yield ext.cell(anchor, "clinical_benefit.binary", None, 0.0,
                           "DERIVED:BOR", "BOR", -1, "derived_bor_binary_no_BOR",
                           notes="BOR is NA → clinical_benefit.binary NA")

    # bor_bin: 120-day SD-landmark rule
    bb_val, bb_conf, bb_note = ext.derive_bor_bin(bin_val, pfs_time_value)
    yield ext.cell(anchor, "bor_bin", bb_val, bb_conf,
                   "DERIVED:BOR.binary+pfs_time", "BOR.binary,pfs_time", -1,
                   "derived_bor_bin_120d",
                   notes=f"{bb_note} | status={_DERIVED_120D_STATUS}")

    # pfs_bin: 120-day landmark rule
    pb_val, pb_conf, pb_note = ext.derive_pfs_bin(pfs_time_value, pfs_stat_value)
    yield ext.cell(anchor, "pfs_bin", pb_val, pb_conf,
                   "DERIVED:pfs_time+pfs_stat", "pfs_time,pfs_stat", -1,
                   "derived_pfs_bin_120d",
                   notes=f"{pb_note} | status={_DERIVED_120D_STATUS}")


def coerce_num(raw_norm):
    try:
        return float(raw_norm) if raw_norm not in (None, "", ".") else None
    except (TypeError, ValueError):
        return None
