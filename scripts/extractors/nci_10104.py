"""10104 extractor — ipilimumab + nivolumab (colon/NSCLC, Arms A/B/C)."""
from __future__ import annotations

import logging
from typing import Iterator

import pandas as pd

from lib.extractor_base import BaseExtractor
from lib.provenance import Cell
from ._helpers import strip_norm, emit_anchor_cells, emit_collection_event_alt, emit_unresolved_derived, coerce_num

LOG = logging.getLogger("nci_10104")


class Extractor(BaseExtractor):
    trial_dir_name = "10104-clinical"
    template_trial_name = "10104"

    def extract(self) -> Iterator[Cell]:
        demo_file  = "10104_demographics.2023-04-04.csv"
        rab_file   = "10104_armaandb_response_pfsos_treatment_update.2023-04-04.csv"
        rc_file    = "10104_armc_response_pfsos_treatment_update16mar2023.2023-04-04.csv"
        arm_ab_file= "10104_armaandb_enrollment_assignment.2023-04-04.csv"
        arm_c_file = "10104_armc_subgroup.2023-04-04.csv"

        demo = self.load_csv("demographics").copy()
        demo = demo[demo["cimac_part_id"].notna()].copy()
        demo["cimac_part_id"] = demo["cimac_part_id"].astype(str)
        demo = demo.drop_duplicates(subset=["cimac_part_id"], keep="first").set_index("cimac_part_id")

        r_ab = self.load_csv("response_aandb").copy()
        r_ab = r_ab[r_ab["cimac_part_id"].notna()].copy()
        r_ab["cimac_part_id"] = r_ab["cimac_part_id"].astype(str)
        r_ab = r_ab.drop_duplicates(subset=["cimac_part_id"], keep="first").set_index("cimac_part_id")

        r_c = self.load_csv("response_armc").copy()
        r_c = r_c[r_c["cimac_part_id"].notna()].copy()
        r_c["cimac_part_id"] = r_c["cimac_part_id"].astype(str)
        r_c = r_c.drop_duplicates(subset=["cimac_part_id"], keep="first").set_index("cimac_part_id")

        arm_ab = self.load_csv("arm_aandb").copy()
        arm_ab = arm_ab[arm_ab["cimac_part_id"].notna()].copy()
        arm_ab["cimac_part_id"] = arm_ab["cimac_part_id"].astype(str)
        arm_ab = arm_ab.drop_duplicates(subset=["cimac_part_id"], keep="first").set_index("cimac_part_id")

        arm_c = self.load_csv("arm_armc").copy()
        arm_c = arm_c[arm_c["cimac_part_id"].notna()].copy()
        arm_c["cimac_part_id"] = arm_c["cimac_part_id"].astype(str)
        arm_c = arm_c.drop_duplicates(subset=["cimac_part_id"], keep="first").set_index("cimac_part_id")

        col_map_demo  = self.cfg.get("column_map", {}).get(demo_file, {})
        resp_cols_ab  = self.cfg.get("response_columns_aandb", {})
        resp_cols_c   = self.cfg.get("response_columns_armc", {})
        trial_vmap    = self.cfg.get("value_maps", {}) or {}
        tx_per_arm    = self.cfg.get("treatment_per_arm", {}) or {}
        ce_alt_map    = self.cfg.get("collection_event_alt_map", {}) or {}
        arm_from_sex  = bool(self.cfg.get("arm_from_sex", False))

        for _, anchor in self.anchor.iterrows():
            pid = str(anchor["cimac_part_id"])
            cur_bor = None
            cur_pfs_stat = None
            cur_pfs_time = None
            gender_raw = None

            yield from emit_anchor_cells(self, anchor)
            yield from emit_collection_event_alt(self, anchor, ce_alt_map)

            # Demographics
            race_fallback_cols = self.cfg.get("race_fallback_columns", []) or []
            if pid in demo.index:
                d = demo.loc[pid]; d_idx = demo.index.get_loc(pid)

                # P2#2: race fallback — try PT_RACE_CD_1, then PT_RACE_CD_2
                if race_fallback_cols:
                    race_raw = None
                    race_src_col = None
                    for c in race_fallback_cols:
                        v = d.get(c)
                        if v is not None and not (isinstance(v, float) and pd.isna(v)) and str(v).strip():
                            race_raw = v
                            race_src_col = c
                            break
                    if race_raw is not None:
                        race_norm = strip_norm(race_raw)
                        mapped = (trial_vmap.get("race") or {}).get(race_norm)
                        if mapped is not None:
                            yield self.cell(anchor, "race", mapped, 0.95,
                                            demo_file, race_src_col, d_idx,
                                            "value_map_trial_with_fallback",
                                            notes=f"{race_src_col}={race_raw!r} → {mapped!r}")
                        else:
                            value, conf, note = self.normalize_value("race", race_raw)
                            yield self.cell(anchor, "race", value, conf,
                                            demo_file, race_src_col, d_idx, "value_map_global",
                                            notes=note)
                    else:
                        yield self.cell(anchor, "race", None, 0.0,
                                        demo_file, "+".join(race_fallback_cols), d_idx,
                                        "no_value_in_fallback_cols",
                                        notes=f"both {race_fallback_cols} are NaN for {pid!r}")

                for src_col, harmonized in col_map_demo.items():
                    # Skip race here — already handled via fallback above
                    if harmonized == "race" and race_fallback_cols:
                        continue
                    raw = d.get(src_col); raw_norm = strip_norm(raw)
                    if src_col == "PRSN_GENDER_CD": gender_raw = raw
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
                    yield self.cell(anchor, harmonized, value, conf, demo_file, src_col, d_idx,
                                    "direct" if conf >= 0.9 else "value_map_global", notes=note)
            else:
                for h in ("race", "sex", "age"):
                    yield self.cell(anchor, h, None, 0.0, demo_file, "cimac_part_id_LOOKUP",
                                    -1, "lookup_miss", notes=f"pid {pid!r} not in demographics")

            # arm = raw PRSN_GENDER_CD value ("Female"/"Male") — template bug
            if arm_from_sex:
                yield self.cell(anchor, "arm", gender_raw,
                                0.85 if pd.notna(gender_raw) else 0.0,
                                demo_file, "PRSN_GENDER_CD (→arm; template bug)",
                                demo.index.get_loc(pid) if pid in demo.index else -1,
                                "template_bug_arm_from_sex",
                                notes="10104 template arm column = raw PRSN_GENDER_CD")

            # Determine which response/arm file the patient lives in
            if pid in r_ab.index:
                r, src_file_used, src_idx, resp_cols, arm_lookup = r_ab.loc[pid], rab_file, r_ab.index.get_loc(pid), resp_cols_ab, arm_ab
            elif pid in r_c.index:
                r, src_file_used, src_idx, resp_cols, arm_lookup = r_c.loc[pid], rc_file, r_c.index.get_loc(pid), resp_cols_c, arm_c
            else:
                r = None; src_file_used = "(no response file match)"; src_idx = -1; resp_cols = {}; arm_lookup = None

            # Treatment by arm
            tx = None
            if pid in arm_ab.index:
                arm_code = strip_norm(arm_ab.loc[pid].get("ENROLL_TX_ASSIGN_CD_STD"))
                tx = tx_per_arm.get(arm_code)
                yield self.cell(anchor, "treatment", tx, 0.95 if tx else 0.30,
                                arm_ab_file, "ENROLL_TX_ASSIGN_CD_STD",
                                arm_ab.index.get_loc(pid), "value_map_trial",
                                notes=f"arm_code={arm_code!r}→treatment={tx!r}")
            elif pid in arm_c.index:
                sub = strip_norm(arm_c.loc[pid].get("subgroup of Arm C"))
                tx = tx_per_arm.get(sub)
                yield self.cell(anchor, "treatment", tx, 0.95 if tx else 0.30,
                                arm_c_file, "subgroup of Arm C",
                                arm_c.index.get_loc(pid), "value_map_trial",
                                notes=f"subgroup={sub!r}→treatment={tx!r}")
            else:
                yield self.cell(anchor, "treatment", None, 0.0,
                                "(neither arm file)", "cimac_part_id_LOOKUP", -1, "lookup_miss")

            # Response fields
            if r is not None:
                for harmonized, src_col in resp_cols.items():
                    raw = r.get(src_col); raw_norm = strip_norm(raw)
                    if harmonized in ("os_time", "pfs_time", "os_stat", "pfs_stat"):
                        v = coerce_num(raw_norm)
                        yield self.cell(anchor, harmonized, v, 0.95 if v is not None else 0.30,
                                        src_file_used, src_col, src_idx, "direct_numeric",
                                        notes=f"{src_col}={raw!r}")
                        if harmonized == "pfs_stat": cur_pfs_stat = v
                        if harmonized == "pfs_time": cur_pfs_time = v
                    elif harmonized == "clinical_benefit":
                        yield self.cell(anchor, "clinical_benefit", raw_norm,
                                        0.95 if raw_norm else 0.0,
                                        src_file_used, src_col, src_idx, "direct",
                                        notes=f"{src_col}={raw!r}")
                        cur_bor = raw_norm

            # phase: NaN in template for 10104
            yield self.cell(anchor, "phase", None, 0.95,
                            "CONFIG:trial_constants", "phase", -1, "trial_constant_NA",
                            notes="10104 phase NA in template")

            # Derived
            yield from emit_unresolved_derived(
                self, anchor,
                bor_value=cur_bor,
                pfs_stat_value=cur_pfs_stat,
                pfs_time_value=cur_pfs_time,
            )
