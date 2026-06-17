"""10013 extractor (NEW trial) — Breast NACT + pembrolizumab.

Builds anchor rows from demographics × specimen_collection (no template anchors).
Cimac.id (sample-level) is NOT present in source — emit NA + flag for review.
"""
from __future__ import annotations

import logging
from typing import Iterator

import pandas as pd

from lib.extractor_base import BaseExtractor
from lib.provenance import Cell
from ._helpers import strip_norm, emit_unresolved_derived, coerce_num

LOG = logging.getLogger("nci_10013")


class Extractor(BaseExtractor):
    trial_dir_name = "10013-clinical"
    template_trial_name = "10013"

    def extract(self) -> Iterator[Cell]:
        demo_file = "demographics_2023-09-13.csv"
        sc_file   = "specimen_collection_2023-09-13.csv"
        resp_file = "response_updated_2024-11-07.csv"

        demo = self.load_csv("demographics").copy()
        demo = demo[demo["cimac_part_id"].notna()].copy()
        demo["cimac_part_id"] = demo["cimac_part_id"].astype(str).str.strip()
        demo = demo[~demo["cimac_part_id"].str.startswith("MISSING")]
        demo = demo.drop_duplicates(subset=["cimac_part_id"], keep="first").set_index("cimac_part_id")

        sc = self.load_csv("sample_coll").copy()
        sc = sc[sc["cimac_part_id"].notna()].copy()
        sc["cimac_part_id"] = sc["cimac_part_id"].astype(str).str.strip()
        sc = sc[~sc["cimac_part_id"].str.startswith("MISSING")]
        # M7 = visit/timepoint string, M4 = sample type
        sc["collection_event"] = sc["M7"].astype(str)

        resp = self.load_csv("response").copy()
        resp = resp[resp["cimac_part_id"].notna()].copy()
        resp["cimac_part_id"] = resp["cimac_part_id"].astype(str).str.strip()
        resp = resp[~resp["cimac_part_id"].str.startswith("MISSING")]
        resp = resp.drop_duplicates(subset=["cimac_part_id"], keep="first").set_index("cimac_part_id")

        # Treatment file: E2 = Treatment Arm (ARM A / ARM B), per Data Dictionary.
        treat_file = "treatment_2023-09-13.csv"
        treat = self.load_csv("treatment").copy()
        treat = treat[treat["cimac_part_id"].notna()].copy()
        treat["cimac_part_id"] = treat["cimac_part_id"].astype(str).str.strip()
        treat = treat.drop_duplicates(subset=["cimac_part_id"], keep="first").set_index("cimac_part_id")

        col_map_demo  = self.cfg.get("column_map", {}).get(demo_file, {})
        col_map_resp  = self.cfg.get("column_map", {}).get(resp_file, {})
        col_map_treat = self.cfg.get("column_map", {}).get(treat_file, {})
        trial_vmap   = self.cfg.get("value_maps", {}) or {}
        trial_consts = self.cfg.get("trial_constants", {}) or {}

        # Build anchor rows: one per (cimac_part_id, M7 timepoint)
        anchor_rows = (
            sc[["cimac_part_id", "collection_event"]]
            .drop_duplicates()
            .reset_index(drop=True)
        )
        LOG.info("10013: constructed %d anchor rows from demographics × specimen_collection", len(anchor_rows))

        for _, ar in anchor_rows.iterrows():
            pid = str(ar["cimac_part_id"])
            ce  = str(ar["collection_event"])
            anchor = pd.Series({"cimac_part_id": pid, "Cimac.id": None, "Collection_Event": ce})

            # Anchor cells — Cimac.id is NA + flagged
            yield self.cell(anchor, "cimac_part_id",   pid, 1.0, demo_file, "cimac_part_id", -1, "constructed_from_source")
            yield self.cell(anchor, "Cimac.id",        None, 0.0, sc_file,
                            "(no sample-level Cimac.id in 10013 source files)", -1, "cimac_id_unavailable",
                            notes="10013 source files do not contain sample-level Cimac.id; external CIMAC manifest required")
            yield self.cell(anchor, "Collection_Event", ce, 0.95, sc_file, "M7", -1, "constructed_from_source")
            yield self.cell(anchor, "trial", self.template_trial_name, 1.0,
                            "CONFIG:trial_dir_to_name", "trial", -1, "trial_constant")
            yield self.cell(anchor, "Collection_Event_alt", None, 0.30,
                            "(no map yet)", "Collection_Event", -1, "value_map_miss",
                            notes=f"raw_ce={ce!r}: no mapping configured for 10013 (flag)")

            cur_bor = None
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
            else:
                for h in ("race", "sex", "age"):
                    yield self.cell(anchor, h, None, 0.0, demo_file, "cimac_part_id_LOOKUP",
                                    -1, "lookup_miss", notes=f"pid {pid!r} not in demographics")

            # Response
            if pid in resp.index:
                r = resp.loc[pid]; r_idx = resp.index.get_loc(pid)
                for src_col, harmonized in col_map_resp.items():
                    raw = r.get(src_col); raw_norm = strip_norm(raw)
                    if harmonized == "clinical_benefit":
                        yield self.cell(anchor, "clinical_benefit", raw_norm, 0.85 if raw_norm else 0.0,
                                        resp_file, src_col, r_idx, "direct",
                                        notes=f"{src_col}={raw!r} (verbose free-text — may need mapping)")
                        cur_bor = raw_norm

            for hfield, val in trial_consts.items():
                yield self.cell(anchor, hfield, val, 0.95,
                                "CONFIG:trial_constants", hfield, -1, "trial_constant")

            # arm from treatment file E2 (Treatment Arm: ARM A / ARM B), verbatim,
            # joined on cimac_part_id. Confirmed source-backed (Data Dictionary).
            arm_src_col = next(iter(col_map_treat), "E2")  # harmonized 'arm' source column (E2)
            if pid in treat.index:
                arm_raw = strip_norm(treat.loc[pid].get(arm_src_col))
                yield self.cell(anchor, "arm", arm_raw, 0.95 if arm_raw else 0.0,
                                treat_file, arm_src_col, treat.index.get_loc(pid),
                                "direct",
                                notes=f"{arm_src_col}={arm_raw!r} (Treatment Arm, verbatim)")
            else:
                yield self.cell(anchor, "arm", None, 0.0, treat_file,
                                "cimac_part_id_LOOKUP", -1, "lookup_miss",
                                notes=f"pid {pid!r} not in treatment file — arm unavailable")
            yield self.cell(anchor, "phase", None, 0.30, "(no source mapping)", "phase",
                            -1, "no_source", notes="10013 phase not derivable from source — flag")
            for h in ("os_time", "os_stat", "pfs_time", "pfs_stat"):
                yield self.cell(anchor, h, None, 0.30, "(no source mapping)", h,
                                -1, "no_source", notes=f"10013 {h} not derivable from response file — flag")

            # 10013 has no derivable PFS time/status from source files.
            # bor_bin/pfs_bin will be NaN; flagged in flagged_for_review.
            yield from emit_unresolved_derived(
                self, anchor,
                bor_value=cur_bor,
                pfs_stat_value=None,
                pfs_time_value=None,
            )
