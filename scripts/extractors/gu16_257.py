"""GU16-257 extractor — urothelial cabozantinib + nivolumab."""
from __future__ import annotations

import logging
from typing import Iterator

import pandas as pd

from lib.extractor_base import BaseExtractor
from lib.provenance import Cell
from ._helpers import strip_norm, emit_anchor_cells, emit_collection_event_alt, emit_unresolved_derived, coerce_num

LOG = logging.getLogger("gu16_257")


class Extractor(BaseExtractor):
    trial_dir_name = "GU16-257-clinical"
    template_trial_name = "CIMAC-gu16257"

    def extract(self) -> Iterator[Cell]:
        demo_file = "patient_demographics.2023-01-04.csv"
        resp_file = "response.2023-01-04.csv"

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
        pfs_time_fallback_cols = self.cfg.get("pfs_time_fallback_columns", []) or []

        for _, anchor in self.anchor.iterrows():
            pid = str(anchor["cimac_part_id"])
            cur_bor = None
            cur_pfs_stat = None
            cur_pfs_time = None

            yield from emit_anchor_cells(self, anchor)
            yield from emit_collection_event_alt(self, anchor, ce_alt_map)

            # Demographics
            if pid in demo.index:
                d = demo.loc[pid]; d_idx = demo.index.get_loc(pid)
                for src_col, harmonized in col_map_demo.items():
                    raw = d.get(src_col); raw_norm = strip_norm(raw)
                    # GU16-257 race is numeric code → look up in value_maps.race
                    if harmonized == "race" and raw_norm is not None:
                        mapped = (trial_vmap.get("race") or {}).get(raw_norm)
                        if mapped is not None:
                            yield self.cell(anchor, "race", mapped, 0.95,
                                            demo_file, src_col, d_idx, "value_map_trial",
                                            notes=f"RACE={raw!r}→{mapped!r}")
                            continue
                    if harmonized == "age":
                        v = coerce_num(raw_norm)
                        yield self.cell(anchor, "age", v, 0.95 if v is not None else 0.0,
                                        demo_file, src_col, d_idx, "direct_numeric",
                                        notes=f"{src_col}={raw!r}")
                        continue
                    # default
                    value, conf, note = self.normalize_value(harmonized, raw)
                    yield self.cell(anchor, harmonized, value, conf,
                                    demo_file, src_col, d_idx,
                                    "direct" if conf >= 0.9 else "value_map_global", notes=note)
            else:
                for h in ("race", "sex", "age"):
                    yield self.cell(anchor, h, None, 0.0, demo_file, "cimac_part_id_LOOKUP",
                                    -1, "lookup_miss", notes=f"pid {pid!r} not in demographics")

            # Response: OSTIM, OSSTAT, DFSTIM, RECCUR, RESPTYPE
            if pid in resp.index:
                r = resp.loc[pid]; r_idx = resp.index.get_loc(pid)
                for src_col, harmonized in col_map_resp.items():
                    raw = r.get(src_col); raw_norm = strip_norm(raw)
                    # value-map check first
                    if harmonized in trial_vmap and raw_norm is not None:
                        mapped = trial_vmap[harmonized].get(raw_norm)
                        if mapped is not None:
                            yield self.cell(anchor, harmonized, mapped, 0.95,
                                            resp_file, src_col, r_idx, "value_map_trial",
                                            notes=f"{src_col}={raw!r}→{mapped!r}")
                            if harmonized == "clinical_benefit": cur_bor = mapped
                            if harmonized == "pfs_stat": cur_pfs_stat = mapped
                            continue
                    # Numeric
                    if harmonized in ("os_time", "pfs_time", "os_stat", "pfs_stat"):
                        v = coerce_num(raw_norm)
                        yield self.cell(anchor, harmonized, v, 0.95 if v is not None else 0.30,
                                        resp_file, src_col, r_idx, "direct_numeric",
                                        notes=f"{src_col}={raw!r}")
                        if harmonized == "pfs_stat": cur_pfs_stat = v
                        if harmonized == "pfs_time": cur_pfs_time = v
                        continue
                    if harmonized == "clinical_benefit":
                        yield self.cell(anchor, "clinical_benefit", raw_norm, 0.95 if raw_norm else 0.0,
                                        resp_file, src_col, r_idx, "direct",
                                        notes=f"{src_col}={raw!r}")
                        cur_bor = raw_norm
                        continue
                    # Generic passthrough for other mapped fields (e.g. phase)
                    yield self.cell(anchor, harmonized, raw_norm,
                                    0.95 if raw_norm else 0.0,
                                    resp_file, src_col, r_idx, "direct",
                                    notes=f"{src_col}={raw!r}")

                # pfs_time: first non-null value from configured fallback list
                if pfs_time_fallback_cols:
                    chosen_col = None
                    chosen_val = None
                    seen = []
                    for c in pfs_time_fallback_cols:
                        v = r.get(c)
                        seen.append(f"{c}={v!r}")
                        if v is not None and not (isinstance(v, float) and pd.isna(v)):
                            chosen_col = c
                            chosen_val = v
                            break
                    if chosen_val is not None:
                        nv = coerce_num(strip_norm(chosen_val))
                        yield self.cell(anchor, "pfs_time", nv,
                                        0.95 if nv is not None else 0.30,
                                        resp_file, chosen_col, r_idx,
                                        "value_with_fallback",
                                        notes=f"first non-null of {pfs_time_fallback_cols}: {'; '.join(seen)}")
                        cur_pfs_time = nv
                    else:
                        yield self.cell(anchor, "pfs_time", None, 0.30,
                                        resp_file, "+".join(pfs_time_fallback_cols), r_idx,
                                        "value_with_fallback_all_null",
                                        notes=f"all fallback cols NaN: {'; '.join(seen)}")
            else:
                for h in ("clinical_benefit", "os_time", "os_stat", "pfs_time", "pfs_stat", "phase"):
                    yield self.cell(anchor, h, None, 0.0, resp_file, "cimac_part_id_LOOKUP",
                                    -1, "lookup_miss", notes=f"pid {pid!r} not in response")

            # phase emitted via response col_map → "METRC" (P1#9 fix; perfect source match).
            # No-op here.

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
