"""9204 extractor — ipi vs nivo post-transplant (paired files per arm)."""
from __future__ import annotations

import logging
from typing import Iterator

import pandas as pd

from lib.extractor_base import BaseExtractor
from lib.provenance import Cell
from ._helpers import strip_norm, emit_anchor_cells, emit_collection_event_alt, emit_unresolved_derived, coerce_num

LOG = logging.getLogger("nci_9204")


class Extractor(BaseExtractor):
    trial_dir_name = "9204-clinical"
    template_trial_name = "CIMAC-9204"

    def extract(self) -> Iterator[Cell]:
        demo_ipi_file  = "demographics_dose_level.ipilimumab_2024-05-01.csv"
        demo_nivo_file = "demographics_dose_level.nivolumab_2024-05-01.csv"
        resp_ipi_file  = "best_response.ipi_2024-05-01.csv"
        resp_nivo_file = "best_response.nivo_2024-05-01.csv"

        def _load_indexed(key):
            df = self.load_csv(key).copy()
            df = df[df["cimac_part_id"].notna()].copy()
            df["cimac_part_id"] = df["cimac_part_id"].astype(str)
            return df.drop_duplicates(subset=["cimac_part_id"], keep="first").set_index("cimac_part_id")

        demo_ipi  = _load_indexed("demographics_ipi")
        demo_nivo = _load_indexed("demographics_nivo")
        resp_ipi  = _load_indexed("response_ipi")
        resp_nivo = _load_indexed("response_nivo")

        col_map_ipi  = self.cfg.get("column_map", {}).get(demo_ipi_file, {})
        col_map_nivo = self.cfg.get("column_map", {}).get(demo_nivo_file, {})
        trial_vmap   = self.cfg.get("value_maps", {}) or {}
        trial_consts = self.cfg.get("trial_constants", {}) or {}
        ce_alt_map   = self.cfg.get("collection_event_alt_map", {}) or {}

        for _, anchor in self.anchor.iterrows():
            pid = str(anchor["cimac_part_id"])
            cur_bor = None

            yield from emit_anchor_cells(self, anchor)
            yield from emit_collection_event_alt(self, anchor, ce_alt_map)

            # Which arm?
            arm_label = None
            if pid in demo_ipi.index:
                arm_label = "ipi"; demo_used, demo_file_used, col_map_used = demo_ipi, demo_ipi_file, col_map_ipi
                resp_used,   resp_file_used = resp_ipi, resp_ipi_file
            elif pid in demo_nivo.index:
                arm_label = "nivo"; demo_used, demo_file_used, col_map_used = demo_nivo, demo_nivo_file, col_map_nivo
                resp_used,   resp_file_used = resp_nivo, resp_nivo_file
            else:
                demo_used = None
                yield self.cell(anchor, "treatment", None, 0.0,
                                "(neither demographics file)", "cimac_part_id_LOOKUP",
                                -1, "lookup_miss",
                                notes=f"pid {pid!r} not in ipi nor nivo demographics")

            # Treatment from arm
            if arm_label:
                yield self.cell(anchor, "treatment", arm_label, 0.95,
                                demo_file_used, "(arm_file_membership)",
                                demo_used.index.get_loc(pid), "trial_arm_from_file",
                                notes=f"pid found in {arm_label} file → treatment={arm_label!r}")

            # Demographics
            if demo_used is not None:
                d = demo_used.loc[pid]; d_idx = demo_used.index.get_loc(pid)
                for src_col, harmonized in col_map_used.items():
                    raw = d.get(src_col); raw_norm = strip_norm(raw)
                    if harmonized in trial_vmap and raw_norm is not None:
                        mapped = trial_vmap[harmonized].get(raw_norm)
                        if mapped is not None:
                            yield self.cell(anchor, harmonized, mapped, 0.95,
                                            demo_file_used, src_col, d_idx, "value_map_trial",
                                            notes=f"{src_col}={raw!r}→{mapped!r}")
                            continue
                    if harmonized == "age":
                        v = coerce_num(raw_norm)
                        yield self.cell(anchor, "age", v, 0.95 if v is not None else 0.0,
                                        demo_file_used, src_col, d_idx, "direct_numeric",
                                        notes=f"{src_col}={raw!r}")
                        continue
                    value, conf, note = self.normalize_value(harmonized, raw)
                    yield self.cell(anchor, harmonized, value, conf,
                                    demo_file_used, src_col, d_idx,
                                    "direct" if conf >= 0.9 else "value_map_global", notes=note)
            else:
                for h in ("race", "sex", "age"):
                    yield self.cell(anchor, h, None, 0.0, "(no demo file)", "cimac_part_id_LOOKUP",
                                    -1, "lookup_miss")

            # clinical_benefit (renamed from BOR) from response file
            if arm_label and pid in resp_used.index:
                r = resp_used.loc[pid]; r_idx = resp_used.index.get_loc(pid)
                raw_bor = strip_norm(r.get("Best Response"))
                yield self.cell(anchor, "clinical_benefit", raw_bor,
                                0.95 if raw_bor else 0.0,
                                resp_file_used, "Best Response", r_idx, "direct",
                                notes=f"Best Response={raw_bor!r}")
                cur_bor = raw_bor
            else:
                yield self.cell(anchor, "clinical_benefit", None, 0.0, "(no response file)",
                                "cimac_part_id_LOOKUP", -1, "lookup_miss")

            # Survival: 9204 template has all NaN for os_stat/pfs_stat — emit NA
            for h in ("os_time", "os_stat", "pfs_time", "pfs_stat"):
                yield self.cell(anchor, h, None, 0.95,
                                "(template all NaN for 9204)", h, -1, "trial_constant_NA",
                                notes="9204 template has no survival data")

            # phase NaN
            yield self.cell(anchor, "phase", None, 0.95,
                            "CONFIG:trial_constants", "phase", -1, "trial_constant_NA",
                            notes="9204 phase NA in template")

            # Trial constants (arm=Others)
            for hfield, val in trial_consts.items():
                yield self.cell(anchor, hfield, val, 0.95,
                                "CONFIG:trial_constants", hfield, -1, "trial_constant")

            # Derived
            # 9204 source has no PFS time/status; pfs_time/pfs_stat are NaN.
            # bor_bin: SD rows will fall to NaN (pfs_time NaN); 9204's template
            # has SD → bor_bin=NaN, so this is consistent.
            yield from emit_unresolved_derived(
                self, anchor,
                bor_value=cur_bor,
                pfs_stat_value=None,
                pfs_time_value=None,
            )
