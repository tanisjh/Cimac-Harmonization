"""E4412 extractor — Hodgkin lymphoma (BV + nivo + ipi); all Excel sources."""
from __future__ import annotations

import logging
from typing import Iterator

import pandas as pd

from lib.extractor_base import BaseExtractor
from lib.provenance import Cell
from ._helpers import strip_norm, emit_anchor_cells, emit_collection_event_alt, emit_unresolved_derived, coerce_num

LOG = logging.getLogger("e4412")


class Extractor(BaseExtractor):
    trial_dir_name = "E4412-clinical"
    template_trial_name = "CIMAC-e4412"

    def extract(self) -> Iterator[Cell]:
        bo_file = "baseline_outcomes.xlsx"
        bo_df = self.load_xlsx("baseline_outcomes", sheet="Sheet1").copy()
        # In source, "CIMAC ID" column equals 7-char cimac_part_id (no sample suffix here).
        bo_df = bo_df[bo_df["CIMAC ID"].notna()].copy()
        bo_df["CIMAC ID"] = bo_df["CIMAC ID"].astype(str).str.strip()
        bo_df = bo_df.drop_duplicates(subset=["CIMAC ID"], keep="first").set_index("CIMAC ID")

        col_map      = self.cfg.get("column_map", {}).get("baseline_outcomes::Sheet1", {})
        trial_vmap   = self.cfg.get("value_maps", {}) or {}
        tx_per_arm   = self.cfg.get("treatment_per_arm", {}) or {}
        trial_consts = self.cfg.get("trial_constants", {}) or {}
        ce_alt_map   = self.cfg.get("collection_event_alt_map", {}) or {}
        time_conv    = self.cfg.get("time_unit_conversion", {}) or {}

        for _, anchor in self.anchor.iterrows():
            pid = str(anchor["cimac_part_id"])
            cur_bor = None
            cur_pfs_stat = None
            cur_pfs_time = None

            yield from emit_anchor_cells(self, anchor)
            yield from emit_collection_event_alt(self, anchor, ce_alt_map)

            if pid in bo_df.index:
                r = bo_df.loc[pid]; r_idx = bo_df.index.get_loc(pid)
                for src_col, harmonized in col_map.items():
                    raw = r.get(src_col); raw_norm = strip_norm(raw)

                    # arm_code → treatment via tx_per_arm
                    if harmonized == "arm_code" and raw_norm is not None:
                        tx = tx_per_arm.get(raw_norm) or tx_per_arm.get("Other")
                        yield self.cell(anchor, "treatment", tx,
                                        0.85 if tx else 0.30,
                                        bo_file, src_col, r_idx, "value_map_trial",
                                        notes=f"arm_code={raw!r}→treatment={tx!r}")
                        continue

                    # Time fields with weeks→days conversion
                    if harmonized in ("os_time_weeks", "pfs_time_weeks"):
                        target = "os_time" if "os" in harmonized else "pfs_time"
                        v = coerce_num(raw_norm)
                        days = round(v * float(time_conv.get(target, 7.0))) if v is not None else None
                        yield self.cell(anchor, target,
                                        float(days) if days is not None else None,
                                        0.95 if days is not None else 0.30,
                                        bo_file, src_col, r_idx,
                                        f"time_unit_conv(×{time_conv.get(target, 7.0)})",
                                        notes=f"{src_col}={raw!r}wk → {days}d")
                        if target == "pfs_time" and days is not None:
                            cur_pfs_time = float(days)
                        continue

                    # Trial value_map check
                    if harmonized in trial_vmap and raw_norm is not None:
                        mapped = trial_vmap[harmonized].get(raw_norm)
                        if mapped is not None:
                            yield self.cell(anchor, harmonized, mapped, 0.95,
                                            bo_file, src_col, r_idx, "value_map_trial",
                                            notes=f"{src_col}={raw!r}→{mapped!r}")
                            if harmonized == "clinical_benefit": cur_bor = mapped
                            continue

                    if harmonized in ("age", "os_stat", "pfs_stat"):
                        v = coerce_num(raw_norm)
                        yield self.cell(anchor, harmonized, v, 0.95 if v is not None else 0.30,
                                        bo_file, src_col, r_idx, "direct_numeric",
                                        notes=f"{src_col}={raw!r}")
                        if harmonized == "pfs_stat": cur_pfs_stat = v
                        continue

                    if harmonized == "clinical_benefit":
                        # Try global value_normalizations.clinical_benefit rules
                        # (e.g., "Unevaluable [<reason>]" → other via contains rule).
                        norm_val, norm_conf, norm_note = self.normalize_value("clinical_benefit", raw)
                        rule_matched = (
                            raw_norm is not None
                            and norm_val != raw_norm
                            and norm_conf >= 0.7
                        )
                        if rule_matched:
                            yield self.cell(anchor, "clinical_benefit", norm_val, norm_conf,
                                            bo_file, src_col, r_idx, "value_map_global",
                                            notes=f"{src_col}={raw!r} → {norm_val!r} ({norm_note})")
                            cur_bor = norm_val
                        else:
                            yield self.cell(anchor, "clinical_benefit", raw_norm, 0.95 if raw_norm else 0.0,
                                            bo_file, src_col, r_idx, "direct",
                                            notes=f"{src_col}={raw!r}")
                            cur_bor = raw_norm
                        continue

                    value, conf, note = self.normalize_value(harmonized, raw)
                    yield self.cell(anchor, harmonized, value, conf, bo_file, src_col, r_idx,
                                    "direct" if conf >= 0.9 else "value_map_global", notes=note)
            else:
                for h in ("race", "sex", "age", "clinical_benefit", "os_time", "os_stat", "pfs_time", "pfs_stat", "treatment"):
                    yield self.cell(anchor, h, None, 0.0, bo_file, "CIMAC_ID_LOOKUP",
                                    -1, "lookup_miss", notes=f"pid {pid!r} not in baseline_outcomes")

            # phase NaN in template
            yield self.cell(anchor, "phase", None, 0.95,
                            "CONFIG:trial_constants", "phase", -1, "trial_constant_NA",
                            notes="E4412 phase NA in template")

            for hfield, val in trial_consts.items():
                yield self.cell(anchor, hfield, val, 0.95,
                                "CONFIG:trial_constants", hfield, -1, "trial_constant")

            yield from emit_unresolved_derived(
                self, anchor,
                bor_value=cur_bor,
                pfs_stat_value=cur_pfs_stat,
                pfs_time_value=cur_pfs_time,
            )
