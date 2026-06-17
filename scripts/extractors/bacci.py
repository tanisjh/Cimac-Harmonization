"""BACCI extractor (NEW trial) — CRC atezolizumab + bevacizumab.

Anchor = specimen_link_out.csv (cimac_part_id, cimac_id, time_to_collection).
This is the only new trial with source-level Cimac.id (column "cimac_id").
"""
from __future__ import annotations

import logging
from typing import Iterator

import pandas as pd

from lib.extractor_base import BaseExtractor
from lib.provenance import Cell
from ._helpers import strip_norm, emit_unresolved_derived, coerce_num

LOG = logging.getLogger("bacci")


class Extractor(BaseExtractor):
    trial_dir_name = "BACCI-clinical"
    template_trial_name = "BACCI"

    def extract(self) -> Iterator[Cell]:
        demo_file = "ru021416i_patient_demo_20220720_2025-03-24.csv"
        sl_file   = "ru021416i_specimen_link_out_20220720_2025-03-24.csv"
        resp_file = "ru021416i_resp_out_20220720_2025-03-24.csv"

        demo = self.load_csv("demographics").copy()
        demo = demo[demo["cimac_part_id"].notna()].copy()
        demo["cimac_part_id"] = demo["cimac_part_id"].astype(str).str.strip()
        demo = demo.drop_duplicates(subset=["cimac_part_id"], keep="first").set_index("cimac_part_id")

        sl = self.load_csv("specimen_link").copy()
        sl = sl[sl["cimac_part_id"].notna()].copy()
        sl["cimac_part_id"] = sl["cimac_part_id"].astype(str).str.strip()

        resp = self.load_csv("response").copy()
        resp = resp[resp["cimac_part_id"].notna()].copy()
        resp["cimac_part_id"] = resp["cimac_part_id"].astype(str).str.strip()
        resp = resp.drop_duplicates(subset=["cimac_part_id"], keep="first").set_index("cimac_part_id")

        col_map_demo = self.cfg.get("column_map", {}).get(demo_file, {})
        col_map_resp = self.cfg.get("column_map", {}).get(resp_file, {})
        trial_vmap   = self.cfg.get("value_maps", {}) or {}
        trial_consts = self.cfg.get("trial_constants", {}) or {}
        arm_col      = self.cfg.get("arm_from_column")

        # Anchor: one row per specimen_link entry (sample-level granularity)
        anchor_rows = sl[["cimac_part_id", "cimac_id", "time_to_collection"]].reset_index(drop=True)
        LOG.info("BACCI: %d anchor rows from specimen_link", len(anchor_rows))

        for _, ar in anchor_rows.iterrows():
            pid    = str(ar["cimac_part_id"])
            cimac_id_raw = strip_norm(ar["cimac_id"])
            ttc    = ar["time_to_collection"]
            ce = f"Day_{int(ttc)}" if pd.notna(ttc) else "Unknown"
            anchor = pd.Series({"cimac_part_id": pid, "Cimac.id": cimac_id_raw, "Collection_Event": ce})

            yield self.cell(anchor, "cimac_part_id",   pid, 1.0, sl_file, "cimac_part_id", -1, "constructed_from_source")
            # Cimac.id is source-derived for BACCI (specimen_link_out.cimac_id)
            if cimac_id_raw and not cimac_id_raw.upper().startswith("MISSING"):
                yield self.cell(anchor, "Cimac.id", cimac_id_raw, 0.95,
                                sl_file, "cimac_id", -1, "source_derived",
                                notes="BACCI specimen_link_out.cimac_id is source-derived")
            else:
                yield self.cell(anchor, "Cimac.id", None, 0.30,
                                sl_file, "cimac_id", -1, "cimac_id_placeholder",
                                notes=f"specimen_link_out.cimac_id={cimac_id_raw!r} — placeholder (no real sample id)")
            yield self.cell(anchor, "Collection_Event", ce, 0.85,
                            sl_file, "time_to_collection",
                            -1, "constructed_from_time_to_collection",
                            notes=f"time_to_collection={ttc!r} → Day_{ttc!r}")
            yield self.cell(anchor, "trial", self.template_trial_name, 1.0,
                            "CONFIG:trial_dir_to_name", "trial", -1, "trial_constant")
            yield self.cell(anchor, "Collection_Event_alt", None, 0.30,
                            "(no map yet)", "Collection_Event", -1, "value_map_miss",
                            notes="BACCI Collection_Event_alt mapping requires Day_X bucketing — flag")

            cur_bor = None
            cur_pfs_stat = None
            # Demographics
            if pid in demo.index:
                d = demo.loc[pid]; d_idx = demo.index.get_loc(pid)
                for src_col, harmonized in col_map_demo.items():
                    raw = d.get(src_col); raw_norm = strip_norm(raw)
                    if harmonized in trial_vmap and raw_norm is not None:
                        mapped = trial_vmap[harmonized].get(raw_norm)
                        if mapped is not None:
                            yield self.cell(anchor, harmonized, mapped, 0.95,
                                            demo_file, src_col, d_idx, "value_map_trial",
                                            notes=f"{src_col}={raw!r}→{mapped!r}")
                            continue
                    if harmonized == "age":
                        v = coerce_num(raw_norm)
                        yield self.cell(anchor, "age", v, 0.95 if v is not None else 0.0,
                                        demo_file, src_col, d_idx, "direct_numeric",
                                        notes=f"{src_col}={raw!r}")
                        continue
                    value, conf, note = self.normalize_value(harmonized, raw)
                    yield self.cell(anchor, harmonized, value, conf,
                                    demo_file, src_col, d_idx,
                                    "direct" if conf >= 0.9 else "value_map_global", notes=note)
                # arm from arm_n
                if arm_col:
                    arm_raw = d.get(arm_col)
                    yield self.cell(anchor, "arm", strip_norm(arm_raw),
                                    0.80 if pd.notna(arm_raw) else 0.0,
                                    demo_file, arm_col, d_idx, "direct",
                                    notes=f"arm from {arm_col}={arm_raw!r} (numeric code — verify)")
            else:
                for h in ("race", "sex", "age", "arm"):
                    yield self.cell(anchor, h, None, 0.0, demo_file, "cimac_part_id_LOOKUP",
                                    -1, "lookup_miss", notes=f"pid {pid!r} not in demographics")

            # Response
            if pid in resp.index:
                r = resp.loc[pid]; r_idx = resp.index.get_loc(pid)
                for src_col, harmonized in col_map_resp.items():
                    raw = r.get(src_col); raw_norm = strip_norm(raw)
                    if harmonized in ("os_time", "pfs_time", "os_stat", "pfs_stat"):
                        v = coerce_num(raw_norm)
                        yield self.cell(anchor, harmonized, v, 0.95 if v is not None else 0.30,
                                        resp_file, src_col, r_idx, "direct_numeric",
                                        notes=f"{src_col}={raw!r}")
                        if harmonized == "pfs_stat": cur_pfs_stat = v
                        continue
                    if harmonized == "BOR":
                        # P2#6: best_response numeric → label via formats.csv OBJ_STAT.
                        # The trial_vmap.BOR is keyed on the float-string form (e.g. "5.0").
                        mapped = (trial_vmap.get("BOR") or {}).get(raw_norm)
                        if mapped is not None:
                            yield self.cell(anchor, "BOR", mapped, 0.95,
                                            resp_file, src_col, r_idx, "value_map_trial",
                                            notes=f"best_response={raw!r}→{mapped!r} (formats.csv OBJ_STAT)")
                            cur_bor = mapped
                        else:
                            yield self.cell(anchor, "BOR", raw_norm, 0.50,
                                            resp_file, src_col, r_idx, "numeric_code_unmapped",
                                            notes=f"best_response={raw!r} not in OBJ_STAT map")
                            cur_bor = raw_norm
            else:
                for h in ("BOR", "os_time", "os_stat", "pfs_time", "pfs_stat"):
                    yield self.cell(anchor, h, None, 0.0, resp_file, "cimac_part_id_LOOKUP",
                                    -1, "lookup_miss", notes=f"pid {pid!r} not in resp_out")

            yield self.cell(anchor, "phase", None, 0.30, "(no source mapping)", "phase",
                            -1, "no_source", notes="BACCI phase not derivable from source")

            for hfield, val in trial_consts.items():
                yield self.cell(anchor, hfield, val, 0.95,
                                "CONFIG:trial_constants", hfield, -1, "trial_constant")

            yield from emit_unresolved_derived(self, anchor, bor_value=cur_bor, pfs_stat_value=cur_pfs_stat)
