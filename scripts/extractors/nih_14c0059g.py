"""14C0059G extractor (NEW NIH trial) — adoptive cell therapy.

Builds anchor rows from demographics × research_sample_collection.Visit.
Cimac.id sample-level is NOT in source — emit NA + flag.
No age column in source — emit NA + flag.
"""
from __future__ import annotations

import logging
from typing import Iterator

import pandas as pd

from lib.extractor_base import BaseExtractor
from lib.provenance import Cell
from ._helpers import strip_norm, emit_unresolved_derived, coerce_num

LOG = logging.getLogger("nih_14c0059g")


class Extractor(BaseExtractor):
    trial_dir_name = "14C0059G-clinical"
    template_trial_name = "14C0059G"

    def extract(self) -> Iterator[Cell]:
        demo_file = "patient_demographics_all.csv"
        sc_file   = "research_sample_collection_apheresis.csv"
        sd_file   = "response_off_treatment_date_of_death.csv"

        demo = self.load_csv("demographics").copy()
        demo = demo[demo["cimac_part_id"].notna()].copy()
        demo["cimac_part_id"] = demo["cimac_part_id"].astype(str).str.strip()
        demo = demo.drop_duplicates(subset=["cimac_part_id"], keep="first").set_index("cimac_part_id")

        sc = self.load_csv("sample_coll").copy()
        sc = sc[sc["cimac_part_id"].notna()].copy()
        sc["cimac_part_id"] = sc["cimac_part_id"].astype(str).str.strip()

        sd = self.load_csv("survival_death").copy()
        sd = sd[sd["cimac_part_id"].notna()].copy()
        sd["cimac_part_id"] = sd["cimac_part_id"].astype(str).str.strip()
        sd = sd.drop_duplicates(subset=["cimac_part_id"], keep="first").set_index("cimac_part_id")

        col_map_demo = self.cfg.get("column_map", {}).get(demo_file, {})
        col_map_sd   = self.cfg.get("column_map", {}).get(sd_file, {})
        trial_vmap   = self.cfg.get("value_maps", {}) or {}
        trial_consts = self.cfg.get("trial_constants", {}) or {}

        # Build anchor rows from sample_coll
        anchor_rows = sc[["cimac_part_id", "Visit"]].rename(
            columns={"Visit": "collection_event"}
        ).drop_duplicates().reset_index(drop=True)
        # Include patients with demographics but no sample collection (baseline-only)
        for pid in set(demo.index) - set(anchor_rows["cimac_part_id"]):
            anchor_rows = pd.concat([anchor_rows,
                                     pd.DataFrame([{"cimac_part_id": pid, "collection_event": "Baseline"}])],
                                    ignore_index=True)
        LOG.info("14C0059G: constructed %d anchor rows", len(anchor_rows))

        for _, ar in anchor_rows.iterrows():
            pid = str(ar["cimac_part_id"])
            ce  = str(ar["collection_event"])
            anchor = pd.Series({"cimac_part_id": pid, "Cimac.id": None, "Collection_Event": ce})

            yield self.cell(anchor, "cimac_part_id",   pid, 1.0, demo_file, "cimac_part_id", -1, "constructed_from_source")
            yield self.cell(anchor, "Cimac.id",        None, 0.0, sc_file,
                            "(no sample-level Cimac.id in 14C0059G source)",
                            -1, "cimac_id_unavailable",
                            notes="14C0059G source has no Cimac.id column; external CIMAC manifest required")
            yield self.cell(anchor, "Collection_Event", ce, 0.95, sc_file, "Visit", -1, "constructed_from_source")
            yield self.cell(anchor, "trial", self.template_trial_name, 1.0,
                            "CONFIG:trial_dir_to_name", "trial", -1, "trial_constant")
            yield self.cell(anchor, "Collection_Event_alt", None, 0.30,
                            "(no map yet)", "Collection_Event", -1, "value_map_miss",
                            notes=f"raw_ce={ce!r}: no mapping configured for 14C0059G")

            cur_bor = None
            cur_pfs_stat = None
            cur_pfs_time = None
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
                    value, conf, note = self.normalize_value(harmonized, raw)
                    yield self.cell(anchor, harmonized, value, conf,
                                    demo_file, src_col, d_idx,
                                    "direct" if conf >= 0.9 else "value_map_global", notes=note)
            else:
                for h in ("race", "sex"):
                    yield self.cell(anchor, h, None, 0.0, demo_file, "cimac_part_id_LOOKUP",
                                    -1, "lookup_miss", notes=f"pid {pid!r} not in demographics")

            # Age: no source column → NA + flag
            yield self.cell(anchor, "age", None, 0.30,
                            demo_file, "(no Age column)", -1, "no_source",
                            notes="14C0059G demographics has no age column — flag for review")

            # Survival/response from sd
            if pid in sd.index:
                r = sd.loc[pid]; r_idx = sd.index.get_loc(pid)
                for src_col, harmonized in col_map_sd.items():
                    raw = r.get(src_col); raw_norm = strip_norm(raw)
                    if harmonized in ("os_time", "pfs_time"):
                        v = coerce_num(raw_norm)
                        yield self.cell(anchor, harmonized, v, 0.95 if v is not None else 0.30,
                                        sd_file, src_col, r_idx, "direct_numeric",
                                        notes=f"{src_col}={raw!r}")
                        if harmonized == "pfs_time": cur_pfs_time = v
                        continue
                    if harmonized == "clinical_benefit":
                        yield self.cell(anchor, "clinical_benefit", raw_norm, 0.95 if raw_norm else 0.0,
                                        sd_file, src_col, r_idx, "direct",
                                        notes=f"{src_col}={raw!r}")
                        cur_bor = raw_norm
            else:
                for h in ("clinical_benefit", "os_time", "pfs_time"):
                    yield self.cell(anchor, h, None, 0.0, sd_file, "cimac_part_id_LOOKUP",
                                    -1, "lookup_miss", notes=f"pid {pid!r} not in survival/death")

            # os_stat / pfs_stat: derive from non-NaN days-to-death/progression
            if pid in sd.index:
                d_death = coerce_num(strip_norm(sd.loc[pid].get("Days to Death")))
                d_prog  = coerce_num(strip_norm(sd.loc[pid].get("Days to Disease Progression")))
                yield self.cell(anchor, "os_stat",
                                1.0 if d_death is not None else 0.0,
                                0.80, sd_file, "Days to Death", sd.index.get_loc(pid),
                                "derived_from_nonnull",
                                notes="os_stat=1 iff Days to Death non-null (convention; flag)")
                yield self.cell(anchor, "pfs_stat",
                                1.0 if d_prog is not None else 0.0,
                                0.80, sd_file, "Days to Disease Progression", sd.index.get_loc(pid),
                                "derived_from_nonnull",
                                notes="pfs_stat=1 iff Days to Disease Progression non-null (convention; flag)")
                cur_pfs_stat = 1.0 if d_prog is not None else 0.0

            yield self.cell(anchor, "arm", None, 0.30, "(no source mapping)", "arm",
                            -1, "no_source", notes="14C0059G arm not derivable from source")
            yield self.cell(anchor, "phase", None, 0.30, "(no source mapping)", "phase",
                            -1, "no_source")

            for hfield, val in trial_consts.items():
                yield self.cell(anchor, hfield, val, 0.95,
                                "CONFIG:trial_constants", hfield, -1, "trial_constant")

            yield from emit_unresolved_derived(
                self, anchor,
                bor_value=cur_bor,
                pfs_stat_value=cur_pfs_stat,
                pfs_time_value=cur_pfs_time,
            )
