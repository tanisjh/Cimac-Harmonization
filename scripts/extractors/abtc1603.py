"""ABTC1603 extractor — glioma trial (Adavosertib + Valproate + Nivolumab + TMZ)."""
from __future__ import annotations

import logging
import re
from typing import Iterator

import pandas as pd

from lib.extractor_base import BaseExtractor
from lib.provenance import Cell

LOG = logging.getLogger("abtc1603")


def _strip_norm(s):
    if s is None or (isinstance(s, float) and pd.isna(s)):
        return None
    return re.sub(r"\s+", " ", str(s)).strip()


class Extractor(BaseExtractor):
    trial_dir_name = "ABTC1603-clinical"
    template_trial_name = "ABTC1603"

    def extract(self) -> Iterator[Cell]:
        demo_file = "abtc_1603_demographic.demographics_2024-04-17.csv"
        resp_file = "abtc_1603_treatmentresponse_03042024_2024-04-17.csv"

        demo = self.load_csv("demographics").copy()
        demo = demo[demo["cimac_part_id"].notna()].copy()
        demo["cimac_part_id"] = demo["cimac_part_id"].astype(str)
        demo = demo.drop_duplicates(subset=["cimac_part_id"], keep="first").set_index("cimac_part_id")

        resp = self.load_csv("response").copy()
        resp = resp[resp["cimac_part_id"].notna()].copy()
        resp["cimac_part_id"] = resp["cimac_part_id"].astype(str)
        resp = resp.drop_duplicates(subset=["cimac_part_id"], keep="first").set_index("cimac_part_id")

        col_map_demo  = self.cfg.get("column_map", {}).get(demo_file, {})
        col_map_resp  = self.cfg.get("column_map", {}).get(resp_file, {})
        ce_alt_map    = self.cfg.get("collection_event_alt_map", {}) or {}
        trial_consts  = self.cfg.get("trial_constants", {}) or {}
        trial_vmap    = self.cfg.get("value_maps", {}) or {}
        arm_from_sex  = bool(self.cfg.get("arm_from_sex", False))

        for _, anchor in self.anchor.iterrows():
            pid = str(anchor["cimac_part_id"])
            cur_pfs_time = None
            cur_pfs_stat = None

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
            gender_raw = None
            if pid in demo.index:
                d = demo.loc[pid]
                d_idx = demo.index.get_loc(pid)
                for src_col, harmonized in col_map_demo.items():
                    raw = d.get(src_col)
                    raw_norm = _strip_norm(raw)
                    if src_col == "Gender":
                        gender_raw = raw

                    # Trial value_map override
                    if harmonized in trial_vmap and raw_norm is not None:
                        mapped = trial_vmap[harmonized].get(raw_norm)
                        if mapped is not None:
                            yield self.cell(anchor, harmonized, mapped, 0.95,
                                            demo_file, src_col, d_idx, "value_map_trial",
                                            notes=f"{src_col}={raw!r} → {mapped!r}")
                            continue

                    # Race/sex: pass through (preserves template casing for ABTC1603)
                    if harmonized in ("race", "sex"):
                        yield self.cell(anchor, harmonized, raw_norm,
                                        0.95 if raw_norm else 0.0,
                                        demo_file, src_col, d_idx, "direct",
                                        notes=f"{src_col}={raw!r} verbatim")
                        continue

                    # Age numeric
                    if harmonized == "age":
                        try:
                            v = float(raw_norm) if raw_norm not in (None, "") else None
                            yield self.cell(anchor, "age", v, 0.95 if v is not None else 0.0,
                                            demo_file, src_col, d_idx, "direct_numeric",
                                            notes=f"Age={raw!r}")
                        except (TypeError, ValueError):
                            yield self.cell(anchor, "age", None, 0.0,
                                            demo_file, src_col, d_idx, "direct_numeric_failed",
                                            notes=f"Age={raw!r} not numeric")
                        continue

                    # Default global normalization
                    value, conf, note = self.normalize_value(harmonized, raw)
                    yield self.cell(anchor, harmonized, value, conf,
                                    demo_file, src_col, d_idx,
                                    "direct" if conf >= 0.9 else "value_map_global",
                                    notes=note or f"{src_col}={raw!r}")
            else:
                for h in ("race", "sex", "age", "phase"):
                    yield self.cell(anchor, h, None, 0.0, demo_file, "cimac_part_id_LOOKUP",
                                    -1, "lookup_miss", notes=f"pid {pid!r} not in demographics")

            # arm = Gender raw value (template bug)
            if arm_from_sex:
                yield self.cell(anchor, "arm", gender_raw,
                                0.85 if pd.notna(gender_raw) else 0.0,
                                demo_file, "Gender (copied into arm — template bug)",
                                demo.index.get_loc(pid) if pid in demo.index else -1,
                                "template_bug_arm_from_sex",
                                notes="ABTC1603 template's arm column = Gender value")

            # Response fields
            if pid in resp.index:
                rrow = resp.loc[pid]
                r_idx = resp.index.get_loc(pid)

                # os_stat from Vital Status (kept from prior pass)
                vital = _strip_norm(rrow.get("Vital Status"))
                if vital is not None:
                    mapped = trial_vmap.get("os_stat", {}).get(vital)
                    if mapped is not None:
                        yield self.cell(anchor, "os_stat", float(mapped), 0.95,
                                        resp_file, "Vital Status", r_idx, "value_map_trial",
                                        notes=f"Vital Status={vital!r} → {mapped}")

                # P2#5: os_time composite — Days to Last Contact for alive, Days to Death for dead
                d_death = rrow.get("Days to Death")
                d_lastc = rrow.get("Days to Last Contact")
                d_prog  = rrow.get("Days to Progression")
                is_dead = vital == "DEAD"
                os_time_v = d_death if is_dead and pd.notna(d_death) else d_lastc
                if pd.notna(os_time_v):
                    yield self.cell(anchor, "os_time", float(os_time_v), 0.93,
                                    resp_file,
                                    "Days to Death (if dead) else Days to Last Contact",
                                    r_idx, "derived_composite",
                                    notes=f"vital={vital!r} → os_time={os_time_v}")

                # P2#5: pfs_time composite — progression > death > last contact
                if pd.notna(d_prog):
                    pfs_time_v, pfs_src = float(d_prog), "Days to Progression"
                elif is_dead and pd.notna(d_death):
                    pfs_time_v, pfs_src = float(d_death), "Days to Death (no progression on record)"
                elif pd.notna(d_lastc):
                    pfs_time_v, pfs_src = float(d_lastc), "Days to Last Contact (censored)"
                else:
                    pfs_time_v, pfs_src = None, "(no source value)"
                yield self.cell(anchor, "pfs_time",
                                pfs_time_v,
                                0.93 if pfs_time_v is not None else 0.0,
                                resp_file, pfs_src, r_idx, "derived_composite",
                                notes=f"vital={vital!r}, d_prog={d_prog!r}, d_death={d_death!r}, d_lastc={d_lastc!r}")
                cur_pfs_time = pfs_time_v
            # pfs_stat derived from Days to Progression non-null
            if pid in resp.index:
                dprog = resp.loc[pid].get("Days to Progression")
                pfs_stat_v = 1.0 if pd.notna(dprog) else 0.0
                yield self.cell(anchor, "pfs_stat", pfs_stat_v, 0.85,
                                resp_file, "Days to Progression", resp.index.get_loc(pid),
                                "derived_from_nonnull",
                                notes=("pfs_stat=1 iff Days to Progression non-null "
                                       "(common convention; flag for review)"))
                cur_pfs_stat = pfs_stat_v

            # clinical_benefit (renamed from BOR): ABTC1603 template has it all NaN,
            # but we still emit the lookup attempt
            yield self.cell(anchor, "clinical_benefit", None, 0.0,
                            resp_file, "(no_BOR_column_in_source)", -1, "not_in_source",
                            notes="ABTC1603 response file has no BOR column; template has clinical_benefit all NaN")

            # Trial constants
            for hfield, val in trial_consts.items():
                yield self.cell(anchor, hfield, val, 0.95,
                                "CONFIG:trial_constants", hfield, -1, "trial_constant")

            # ABTC1603 has no BOR — but template BOR.binary is the constant
            # "other" for all 148 rows (P1#3 fix). Emitted via trial_constants.
            # Under the 120-day rule, BOR.binary='other' → bor_bin=NaN (matches template).
            # pfs_bin: use the 120-day rule against the composite pfs_time + pfs_stat.
            bb_val, bb_conf, bb_note = self.derive_bor_bin("other", cur_pfs_time)
            yield self.cell(anchor, "bor_bin", bb_val, bb_conf,
                            "DERIVED:BOR.binary+pfs_time",
                            "BOR.binary(=other constant),pfs_time", -1,
                            "derived_bor_bin_120d",
                            notes=f"{bb_note} | ABTC1603 BOR.binary='other' → bor_bin=NaN | status=120-day landmark; pending final clinical confirmation")

            pb_val, pb_conf, pb_note = self.derive_pfs_bin(cur_pfs_time, cur_pfs_stat)
            yield self.cell(anchor, "pfs_bin", pb_val, pb_conf,
                            "DERIVED:pfs_time+pfs_stat", "pfs_time,pfs_stat", -1,
                            "derived_pfs_bin_120d",
                            notes=f"{pb_note} | status=120-day landmark; template-supported derived rule, pending final clinical confirmation")
