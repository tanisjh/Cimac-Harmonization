"""10021 extractor — durvalumab + tremelimumab + RT (colon/lung)."""
from __future__ import annotations

import logging
from typing import Iterator

import pandas as pd

from lib.extractor_base import BaseExtractor
from lib.provenance import Cell
from ._helpers import strip_norm, emit_anchor_cells, emit_collection_event_alt, emit_unresolved_derived, coerce_num

LOG = logging.getLogger("nci_10021")


class Extractor(BaseExtractor):
    trial_dir_name = "10021-clinical"
    template_trial_name = "CIMAC-10021"

    def extract(self) -> Iterator[Cell]:
        all_file = "10021_AllPatientData.2023-06-20.csv"
        df = self.load_csv("all_patient").copy()
        df = df[df["cimac_part_id"].notna()].copy()
        df["cimac_part_id"] = df["cimac_part_id"].astype(str)
        df = df.drop_duplicates(subset=["cimac_part_id"], keep="first").set_index("cimac_part_id")

        col_map      = self.cfg.get("column_map", {}).get(all_file, {})
        trial_vmap   = self.cfg.get("value_maps", {}) or {}
        trial_consts = self.cfg.get("trial_constants", {}) or {}
        ce_alt_map   = self.cfg.get("collection_event_alt_map", {}) or {}

        for _, anchor in self.anchor.iterrows():
            pid = str(anchor["cimac_part_id"])
            cur_bor = None
            cur_pfs_stat = None
            cur_pfs_time = None

            yield from emit_anchor_cells(self, anchor)
            yield from emit_collection_event_alt(self, anchor, ce_alt_map)

            if pid in df.index:
                d = df.loc[pid]; d_idx = df.index.get_loc(pid)
                for src_col, harmonized in col_map.items():
                    raw = d.get(src_col); raw_norm = strip_norm(raw)
                    # value_map check
                    if harmonized in trial_vmap and raw_norm is not None:
                        mapped = trial_vmap[harmonized].get(raw_norm)
                        if mapped is not None:
                            yield self.cell(anchor, harmonized, mapped, 0.95,
                                            all_file, src_col, d_idx, "value_map_trial",
                                            notes=f"{src_col}={raw!r}→{mapped!r}")
                            if harmonized == "clinical_benefit": cur_bor = mapped
                            continue
                    # numeric
                    if harmonized in ("age", "os_time", "pfs_time", "os_stat", "pfs_stat"):
                        v = coerce_num(raw_norm)
                        yield self.cell(anchor, harmonized, v, 0.95 if v is not None else 0.30,
                                        all_file, src_col, d_idx, "direct_numeric",
                                        notes=f"{src_col}={raw!r}")
                        if harmonized == "pfs_stat": cur_pfs_stat = v
                        if harmonized == "pfs_time": cur_pfs_time = v
                        continue
                    # passthrough (phase, treatment, etc.)
                    yield self.cell(anchor, harmonized, raw_norm,
                                    0.95 if raw_norm else 0.0,
                                    all_file, src_col, d_idx, "direct",
                                    notes=f"{src_col}={raw!r}")
                    if harmonized == "clinical_benefit": cur_bor = raw_norm
            else:
                for h in ("race", "sex", "age", "phase", "treatment", "clinical_benefit",
                          "os_time", "os_stat", "pfs_time", "pfs_stat"):
                    yield self.cell(anchor, h, None, 0.0, all_file, "cimac_part_id_LOOKUP",
                                    -1, "lookup_miss", notes=f"pid {pid!r} not in AllPatientData")

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
