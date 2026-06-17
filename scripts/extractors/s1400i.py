"""S1400I extractor — Lung-MAP S1400I."""
from __future__ import annotations

import logging
import re
from typing import Iterator

import pandas as pd

from lib.extractor_base import BaseExtractor
from lib.provenance import Cell

LOG = logging.getLogger("s1400i")


def _strip_normalize(s):
    """Strip and collapse whitespace+newlines for value_map lookups."""
    if s is None or (isinstance(s, float) and pd.isna(s)):
        return None
    return re.sub(r"\s+", " ", str(s)).strip()


class Extractor(BaseExtractor):
    trial_dir_name = "S1400I-clinical"
    template_trial_name = "CIMAC-s1400i"

    def extract(self) -> Iterator[Cell]:
        df = self.load_csv("clinical")
        df = df.copy()
        df["cimac_part_id"] = df["cimac_part_id"].astype(str)
        df = df.drop_duplicates(subset=["cimac_part_id"], keep="first").set_index("cimac_part_id")

        src_file        = "Clinical Dataset 2023_03_14.csv"
        column_map      = self.cfg.get("column_map", {}).get(src_file, {})
        trial_consts    = self.cfg.get("trial_constants", {}) or {}
        trial_value_map = self.cfg.get("value_maps", {}) or {}
        ce_alt_map      = self.cfg.get("collection_event_alt_map", {}) or {}
        phase_prefix    = self.cfg.get("phase_from_cimac_prefix", {}) or {}
        time_unit_conv  = self.cfg.get("time_unit_conversion", {}) or {}

        for _, anchor in self.anchor.iterrows():
            pid = str(anchor["cimac_part_id"])
            cur_bor = None
            cur_pfs_stat = None
            cur_pfs_time = None

            # Anchor columns
            yield self.cell(anchor, "cimac_part_id",    pid,                            1.0, src_file, "cimac_part_id", -1, "direct")
            yield self.cell(anchor, "Cimac.id",         str(anchor["Cimac.id"]),        1.0, "TEMPLATE_ANCHOR", "Cimac.id", -1, "template_anchor_only")
            yield self.cell(anchor, "Collection_Event", str(anchor["Collection_Event"]),1.0, "TEMPLATE_ANCHOR", "Collection_Event", -1, "template_anchor_only")
            yield self.cell(anchor, "trial",            self.template_trial_name,       1.0, "CONFIG:trial_dir_to_name", "trial", -1, "trial_constant")

            # Collection_Event_alt derivation
            raw_ce = str(anchor["Collection_Event"])
            ce_alt = ce_alt_map.get(raw_ce)
            if ce_alt:
                yield self.cell(anchor, "Collection_Event_alt", ce_alt, 0.95,
                                "CONFIG:collection_event_alt_map", "Collection_Event", -1,
                                "value_map_collection_event")
            else:
                yield self.cell(anchor, "Collection_Event_alt", None, 0.30,
                                "CONFIG:collection_event_alt_map", "Collection_Event", -1,
                                "value_map_miss",
                                notes=f"No mapping for Collection_Event={raw_ce!r}")

            if pid not in df.index:
                yield self.cell(anchor, "cimac_part_id_LOOKUP", None, 0.0,
                                src_file, "cimac_part_id", -1, "lookup_miss",
                                notes=f"pid {pid!r} not in source")
                continue

            src_row = df.loc[pid]
            src_idx = df.index.get_loc(pid)

            # Mapped fields
            for src_col, harmonized in column_map.items():
                raw = src_row.get(src_col)
                raw_norm = _strip_normalize(raw)

                # 1) Trial-specific value_map
                if harmonized in trial_value_map and raw_norm is not None:
                    proposed = trial_value_map[harmonized].get(raw_norm)
                    if proposed is not None:
                        yield self.cell(anchor, harmonized, proposed, 0.95,
                                        src_file, src_col, src_idx, "value_map_trial",
                                        notes=f"{src_col}={raw!r} → {proposed!r}")
                        if harmonized == "clinical_benefit":   cur_bor = proposed
                        if harmonized == "pfs_stat": cur_pfs_stat = proposed
                        continue

                # 2) Time-unit conversion
                if harmonized in time_unit_conv and raw_norm is not None:
                    try:
                        days = float(raw_norm) * float(time_unit_conv[harmonized])
                        days = round(days)
                        yield self.cell(anchor, harmonized, float(days), 0.95,
                                        src_file, src_col, src_idx,
                                        f"time_unit_conv(×{time_unit_conv[harmonized]})",
                                        notes=f"{src_col}={raw!r} months → {days} days")
                        if harmonized == "pfs_time": cur_pfs_time = float(days)
                        continue
                    except (TypeError, ValueError):
                        pass

                # 3) Global normalization. Special-case age: source is integer
                # `age_num` (age at enrollment). Template carries decimal age at
                # sample collection which was truncated upstream at the CIDC step
                # and cannot be recovered from any S1400I source file. Per reviewer
                # decision 2026-05-20, substitute the integer enrollment age and
                # emit with high confidence so the cell flows through (was 0.55,
                # which fell below the 0.80 per-field threshold and produced
                # 561 NA + flagged cells).
                if harmonized == "age":
                    try:
                        v = float(raw_norm) if raw_norm not in (None, ".") else None
                    except (TypeError, ValueError):
                        v = None
                    yield self.cell(anchor, "age", v, 0.95 if v is not None else 0.0,
                                    src_file, src_col, src_idx,
                                    "age_at_enrollment_integer_substitute",
                                    notes=(
                                        "Reviewer-approved substitute (2026-05-20): integer "
                                        "age_num at enrollment used in place of template decimal "
                                        "age. Decimal age was truncated upstream at the CIDC step "
                                        "and is not recoverable from any S1400I source file."
                                    ))
                    continue

                value, conf, note = self.normalize_value(harmonized, raw)
                yield self.cell(anchor, harmonized, value, conf, src_file, src_col, src_idx,
                                "direct" if conf >= 0.9 else "value_map_global",
                                notes=note or f"{src_col}={raw!r}")
                if harmonized == "clinical_benefit" and value is not None: cur_bor = value
                if harmonized == "pfs_stat" and value is not None:   cur_pfs_stat = value

            # phase: from cimac_part_id prefix
            prefix = pid[:4]
            phase_val = phase_prefix.get(prefix)
            if phase_val:
                yield self.cell(anchor, "phase", phase_val, 0.95,
                                "DERIVED:cimac_part_id_prefix", "cimac_part_id[:4]", src_idx,
                                "phase_from_prefix",
                                notes=f"cimac_part_id prefix {prefix!r} → phase {phase_val!r}")
            else:
                yield self.cell(anchor, "phase", None, 0.30,
                                "DERIVED:cimac_part_id_prefix", "cimac_part_id[:4]", src_idx,
                                "phase_from_prefix_miss",
                                notes=f"prefix {prefix!r} not in phase_from_cimac_prefix")

            # Trial-constants
            for hfield, val in trial_consts.items():
                yield self.cell(anchor, hfield, val, 0.95,
                                "CONFIG:trial_constants", hfield, -1, "trial_constant")

            # Derive clinical_benefit.binary, bor_bin (120-day SD-landmark), pfs_bin (120-day)
            bin_val, bin_conf, bin_note = self.derive_BOR_binary(cur_bor)
            if bin_val is not None:
                yield self.cell(anchor, "clinical_benefit.binary", bin_val, bin_conf,
                                "DERIVED:BOR", "BOR", src_idx, "derived_bor_binary",
                                notes=bin_note)
            else:
                yield self.cell(anchor, "clinical_benefit.binary", None, 0.0,
                                "DERIVED:BOR", "BOR", src_idx, "derived_bor_binary_no_BOR",
                                notes="BOR is NA → clinical_benefit.binary NA")

            bb_val, bb_conf, bb_note = self.derive_bor_bin(bin_val, cur_pfs_time)
            yield self.cell(anchor, "bor_bin", bb_val, bb_conf,
                            "DERIVED:BOR.binary+pfs_time", "BOR.binary,pfs_time", src_idx,
                            "derived_bor_bin_120d",
                            notes=f"{bb_note} | status=120-day landmark; template-supported derived rule, pending final clinical confirmation")

            pb_val, pb_conf, pb_note = self.derive_pfs_bin(cur_pfs_time, cur_pfs_stat)
            yield self.cell(anchor, "pfs_bin", pb_val, pb_conf,
                            "DERIVED:pfs_time+pfs_stat", "pfs_time,pfs_stat", src_idx,
                            "derived_pfs_bin_120d",
                            notes=f"{pb_note} | status=120-day landmark; template-supported derived rule, pending final clinical confirmation")
