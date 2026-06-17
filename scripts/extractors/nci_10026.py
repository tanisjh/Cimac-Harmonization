"""10026 extractor — ipilimumab + decitabine (AML/MDS/MF)."""
from __future__ import annotations

import logging
from typing import Iterator

import pandas as pd

from lib.extractor_base import BaseExtractor
from lib.provenance import Cell
from ._helpers import strip_norm, emit_anchor_cells, emit_collection_event_alt, emit_unresolved_derived, coerce_num

LOG = logging.getLogger("nci_10026")


class Extractor(BaseExtractor):
    trial_dir_name = "10026-clinical"
    template_trial_name = "10026"

    def extract(self) -> Iterator[Cell]:
        demo_file = "demographics_04282024.csv"
        resp_file = "response_04282024.csv"

        demo = self.load_csv("demographics").copy()
        demo = demo[demo["cimac_part_id"].notna()].copy()
        demo["cimac_part_id"] = demo["cimac_part_id"].astype(str)
        demo = demo.drop_duplicates(subset=["cimac_part_id"], keep="first").set_index("cimac_part_id")

        resp = self.load_csv("response").copy()
        resp = resp[resp["cimac_part_id"].notna()].copy()
        resp["cimac_part_id"] = resp["cimac_part_id"].astype(str)
        resp = resp.drop_duplicates(subset=["cimac_part_id"], keep="first").set_index("cimac_part_id")

        col_map_demo = self.cfg.get("column_map", {}).get(demo_file, {})
        col_map_resp = self.cfg.get("column_map", {}).get(resp_file, {})
        trial_vmap   = self.cfg.get("value_maps", {}) or {}
        trial_consts = self.cfg.get("trial_constants", {}) or {}
        ce_alt_map   = self.cfg.get("collection_event_alt_map", {}) or {}
        arm_from_sex = bool(self.cfg.get("arm_from_sex", False))

        for _, anchor in self.anchor.iterrows():
            pid = str(anchor["cimac_part_id"])
            cur_bor = None
            cur_pfs_stat = None
            cur_pfs_time = None

            yield from emit_anchor_cells(self, anchor)
            yield from emit_collection_event_alt(self, anchor, ce_alt_map)

            # Demographics
            a3_raw = None
            if pid in demo.index:
                d = demo.loc[pid]; d_idx = demo.index.get_loc(pid)
                for src_col, harmonized in col_map_demo.items():
                    raw = d.get(src_col); raw_norm = strip_norm(raw)
                    if src_col == "A3": a3_raw = raw
                    # Trial vmap
                    if harmonized in trial_vmap and raw_norm is not None:
                        mapped = trial_vmap[harmonized].get(raw_norm)
                        if mapped is not None:
                            yield self.cell(anchor, harmonized, mapped, 0.95,
                                            demo_file, src_col, d_idx, "value_map_trial",
                                            notes=f"{src_col}={raw!r}→{mapped!r}")
                            continue
                    # Age numeric
                    if harmonized == "age":
                        v = coerce_num(raw_norm)
                        yield self.cell(anchor, "age", v, 0.95 if v is not None else 0.0,
                                        demo_file, src_col, d_idx, "direct_numeric",
                                        notes=f"{src_col}={raw!r}")
                        continue
                    # Default normalize
                    value, conf, note = self.normalize_value(harmonized, raw)
                    yield self.cell(anchor, harmonized, value, conf,
                                    demo_file, src_col, d_idx,
                                    "direct" if conf >= 0.9 else "value_map_global", notes=note)
            else:
                for h in ("race", "sex", "age"):
                    yield self.cell(anchor, h, None, 0.0, demo_file, "cimac_part_id_LOOKUP",
                                    -1, "lookup_miss", notes=f"pid {pid!r} not in demographics")

            # arm = raw A3 (sex) value (template bug — verbatim "Male"/"Female")
            if arm_from_sex:
                yield self.cell(anchor, "arm", a3_raw,
                                0.85 if pd.notna(a3_raw) else 0.0,
                                demo_file, "A3 (copied → arm; template bug)",
                                demo.index.get_loc(pid) if pid in demo.index else -1,
                                "template_bug_arm_from_sex",
                                notes="10026 template arm column = raw A3 (Gender) verbatim")

            # Response fields
            if pid in resp.index:
                r = resp.loc[pid]; r_idx = resp.index.get_loc(pid)
                for src_col, harmonized in col_map_resp.items():
                    raw = r.get(src_col); raw_norm = strip_norm(raw)
                    # Value map
                    if harmonized in trial_vmap and raw_norm is not None:
                        mapped = trial_vmap[harmonized].get(raw_norm)
                        if mapped is not None:
                            yield self.cell(anchor, harmonized, mapped, 0.95,
                                            resp_file, src_col, r_idx, "value_map_trial",
                                            notes=f"{src_col}={raw!r}→{mapped!r}")
                            if harmonized == "pfs_stat": cur_pfs_stat = mapped
                            continue
                    # Numeric fields (os_time, pfs_time, etc.)
                    if harmonized in ("os_time", "pfs_time", "os_stat", "pfs_stat"):
                        v = coerce_num(raw_norm)
                        yield self.cell(anchor, harmonized, v, 0.95 if v is not None else 0.30,
                                        resp_file, src_col, r_idx, "direct_numeric",
                                        notes=f"{src_col}={raw!r}")
                        if harmonized == "pfs_stat": cur_pfs_stat = v
                        if harmonized == "pfs_time": cur_pfs_time = v
                        continue
                    # clinical_benefit (renamed from BOR) — string passthrough
                    if harmonized == "clinical_benefit":
                        yield self.cell(anchor, "clinical_benefit", raw_norm, 0.95 if raw_norm else 0.0,
                                        resp_file, src_col, r_idx, "direct",
                                        notes=f"{src_col}={raw!r}")
                        cur_bor = raw_norm
                        continue
                    # default
                    value, conf, note = self.normalize_value(harmonized, raw)
                    yield self.cell(anchor, harmonized, value, conf,
                                    resp_file, src_col, r_idx, "value_map_global", notes=note)
            else:
                for h in ("clinical_benefit", "os_time", "os_stat", "pfs_time", "pfs_stat"):
                    yield self.cell(anchor, h, None, 0.0, resp_file, "cimac_part_id_LOOKUP",
                                    -1, "lookup_miss", notes=f"pid {pid!r} not in response")

            # phase = NaN in template for 10026
            yield self.cell(anchor, "phase", None, 0.95,
                            "CONFIG:trial_constants", "phase", -1, "trial_constant_NA",
                            notes="10026 phase is NA in template")

            # Trial constants
            for hfield, val in trial_consts.items():
                yield self.cell(anchor, hfield, val, 0.95,
                                "CONFIG:trial_constants", hfield, -1, "trial_constant")

            # Derived
            yield from emit_unresolved_derived(
                self, anchor,
                bor_value=cur_bor,
                pfs_stat_value=cur_pfs_stat,
                pfs_time_value=cur_pfs_time,
            )
