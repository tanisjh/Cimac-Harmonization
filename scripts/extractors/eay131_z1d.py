"""EAY131-Z1D extractor — NCI-MATCH arm Z1D (nivolumab)."""
from __future__ import annotations

import logging
import re
from typing import Iterator

import pandas as pd

from lib.extractor_base import BaseExtractor
from lib.provenance import Cell

LOG = logging.getLogger("eay131_z1d")


def _strip_norm(s):
    if s is None or (isinstance(s, float) and pd.isna(s)):
        return None
    return re.sub(r"\s+", " ", str(s)).strip()


class Extractor(BaseExtractor):
    trial_dir_name = "EAY131-Z1D-clinical"
    template_trial_name = "EAY131_Z1D"

    def extract(self) -> Iterator[Cell]:
        # Demographics
        demo = self.load_csv("demographics").copy()
        if self.cfg.get("skip_header_row_when_cimac_part_id_blank", False):
            demo = demo[demo["cimac_part_id"].notna()].copy()
        demo["cimac_part_id"] = demo["cimac_part_id"].astype(str)
        demo = demo.drop_duplicates(subset=["cimac_part_id"], keep="first").set_index("cimac_part_id")

        # Response
        resp_file = self.cfg.get("response_file", "response_2023-09-25.csv")
        resp_df = self.load_csv("response").copy()
        resp_df = resp_df[resp_df["cimac_part_id"].notna()].copy()
        resp_df["cimac_part_id"] = resp_df["cimac_part_id"].astype(str)
        resp_df = resp_df.drop_duplicates(subset=["cimac_part_id"], keep="first").set_index("cimac_part_id")

        column_map_demo  = self.cfg.get("column_map", {}).get("demographics_2023-09-25.csv", {})
        response_map     = self.cfg.get("response_column_map", {}) or {}
        trial_consts     = self.cfg.get("trial_constants", {}) or {}
        trial_value_map  = self.cfg.get("value_maps", {}) or {}
        ce_alt_map       = self.cfg.get("collection_event_alt_map", {}) or {}
        arm_from_sex     = bool(self.cfg.get("arm_from_sex", False))
        demo_file        = "demographics_2023-09-25.csv"

        for i, anchor in self.anchor.iterrows():
            pid = str(anchor["cimac_part_id"])
            cur_bor = None
            cur_pfs_stat = None
            cur_pfs_time = None

            # Anchors
            yield self.cell(anchor, "cimac_part_id",    pid,                            1.0, "TEMPLATE_ANCHOR", "cimac_part_id", -1, "template_anchor_only")
            yield self.cell(anchor, "Cimac.id",         str(anchor["Cimac.id"]),        1.0, "TEMPLATE_ANCHOR", "Cimac.id", -1, "template_anchor_only")
            yield self.cell(anchor, "Collection_Event", str(anchor["Collection_Event"]),1.0, "TEMPLATE_ANCHOR", "Collection_Event", -1, "template_anchor_only")
            yield self.cell(anchor, "trial",            self.template_trial_name,       1.0, "CONFIG:trial_dir_to_name", "trial", -1, "trial_constant")

            # Collection_Event_alt
            raw_ce = str(anchor["Collection_Event"])
            ce_alt = ce_alt_map.get(raw_ce)
            yield self.cell(anchor, "Collection_Event_alt", ce_alt,
                            0.95 if ce_alt else 0.30,
                            "CONFIG:collection_event_alt_map", "Collection_Event", -1,
                            "value_map_collection_event",
                            notes=f"raw_ce={raw_ce!r}" + (f" → {ce_alt!r}" if ce_alt else " (unmapped)"))

            # Demographics fields
            src_a3_value = None
            if pid in demo.index:
                src_row = demo.loc[pid]
                src_idx = demo.index.get_loc(pid)
                for src_col, harmonized in column_map_demo.items():
                    if harmonized == "native_pid":
                        continue
                    raw = src_row.get(src_col)
                    raw_norm = _strip_norm(raw)
                    if src_col == "A3":
                        src_a3_value = raw   # for arm bug
                    if harmonized in trial_value_map and raw_norm is not None:
                        mapped = trial_value_map[harmonized].get(raw_norm)
                        if mapped is not None:
                            yield self.cell(anchor, harmonized, mapped, 0.95,
                                            demo_file, src_col, src_idx, "value_map_trial",
                                            notes=f"{src_col}={raw!r} → {mapped!r}")
                            continue
                    value, conf, note = self.normalize_value(harmonized, raw)
                    yield self.cell(anchor, harmonized, value, conf,
                                    demo_file, src_col, src_idx,
                                    "direct" if conf >= 0.9 else "value_map_global",
                                    notes=note or f"{src_col}={raw!r}")
            else:
                for harmonized in ("race", "sex", "age"):
                    yield self.cell(anchor, harmonized, None, 0.0,
                                    demo_file, "cimac_part_id_LOOKUP", -1, "lookup_miss",
                                    notes=f"pid {pid!r} not in demographics")

            # arm: reproduce template bug (= raw A3 value)
            if arm_from_sex:
                yield self.cell(anchor, "arm", src_a3_value,
                                0.85 if pd.notna(src_a3_value) else 0.0,
                                demo_file, "A3 (copied into arm — template bug)",
                                demo.index.get_loc(pid) if pid in demo.index else -1,
                                "template_bug_arm_from_sex",
                                notes="Template's `arm` reproduces A3 (gender) value verbatim")

            # Response file fields
            if pid in resp_df.index:
                rrow = resp_df.loc[pid]
                rsrc_idx = resp_df.index.get_loc(pid)
                for src_col, harmonized in response_map.items():
                    raw = rrow.get(src_col)
                    raw_norm = _strip_norm(raw)
                    # Numeric coerce for time/stat fields
                    if harmonized in ("os_time", "pfs_time", "os_stat", "pfs_stat") and raw_norm is not None:
                        try:
                            value = float(raw_norm)
                            yield self.cell(anchor, harmonized, value, 0.95,
                                            resp_file, src_col, rsrc_idx, "direct_numeric",
                                            notes=f"{src_col}={raw!r}")
                            if harmonized == "pfs_stat":
                                cur_pfs_stat = value
                            if harmonized == "pfs_time":
                                cur_pfs_time = value
                            continue
                        except (TypeError, ValueError):
                            pass
                    # clinical_benefit (renamed from BOR) — string passthrough
                    if harmonized == "clinical_benefit":
                        yield self.cell(anchor, "clinical_benefit", raw_norm, 0.95 if raw_norm else 0.0,
                                        resp_file, src_col, rsrc_idx, "direct",
                                        notes=f"{src_col}={raw!r}")
                        cur_bor = raw_norm
                        continue
                    value, conf, note = self.normalize_value(harmonized, raw)
                    yield self.cell(anchor, harmonized, value, conf,
                                    resp_file, src_col, rsrc_idx, "value_map_global", notes=note)
            else:
                for harmonized in ("clinical_benefit", "os_time", "os_stat", "pfs_time", "pfs_stat"):
                    yield self.cell(anchor, harmonized, None, 0.0,
                                    resp_file, "cimac_part_id_LOOKUP", -1, "lookup_miss",
                                    notes=f"pid {pid!r} not in response file")

            # Trial constants
            for hfield, val in trial_consts.items():
                yield self.cell(anchor, hfield, val, 0.95,
                                "CONFIG:trial_constants", hfield, -1, "trial_constant")

            # Derive clinical_benefit.binary, bor_bin (120-day SD-landmark), pfs_bin (120-day)
            bin_val, bin_conf, bin_note = self.derive_BOR_binary(cur_bor)
            if bin_val is not None:
                yield self.cell(anchor, "clinical_benefit.binary", bin_val, bin_conf,
                                "DERIVED:BOR", "BOR", -1, "derived_bor_binary", notes=bin_note)
            else:
                yield self.cell(anchor, "clinical_benefit.binary", None, 0.0,
                                "DERIVED:BOR", "BOR", -1, "derived_bor_binary_no_BOR",
                                notes="BOR is NA → clinical_benefit.binary NA")

            bb_val, bb_conf, bb_note = self.derive_bor_bin(bin_val, cur_pfs_time)
            yield self.cell(anchor, "bor_bin", bb_val, bb_conf,
                            "DERIVED:BOR.binary+pfs_time", "BOR.binary,pfs_time", -1,
                            "derived_bor_bin_120d",
                            notes=f"{bb_note} | status=120-day landmark; template-supported derived rule, pending final clinical confirmation")

            pb_val, pb_conf, pb_note = self.derive_pfs_bin(cur_pfs_time, cur_pfs_stat)
            yield self.cell(anchor, "pfs_bin", pb_val, pb_conf,
                            "DERIVED:pfs_time+pfs_stat", "pfs_time,pfs_stat", -1,
                            "derived_pfs_bin_120d",
                            notes=f"{pb_note} | status=120-day landmark; template-supported derived rule, pending final clinical confirmation")
