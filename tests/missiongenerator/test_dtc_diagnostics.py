from __future__ import annotations

import json
import zipfile
from pathlib import Path

from game.missiongenerator.dtc.diagnostics import diff_miz_dtc, inspect_miz_dtc


def _write_miz(miz: Path, members: dict[str, dict[str, object]]) -> None:
    with zipfile.ZipFile(miz, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("mission", "mission = {}")
        for name, payload in members.items():
            z.writestr(name, json.dumps(payload))


def test_inspect_miz_dtc_summarizes_known_partitions(tmp_path: Path) -> None:
    miz = tmp_path / "sample.miz"
    _write_miz(
        miz,
        {
            "DTC/FA-18C Lot 20 DTC_1.dtc": {
                "name": "FA-18C Lot 20 DTC_1",
                "type": "FA-18C_hornet",
                "data": {
                    "name": "",
                    "type": "FA-18C_hornet",
                    "terrain": "Syria",
                    "SA": {
                        "MEZ_THRTS": [{"id": "1"}],
                        "CAP_PTS": [{"id": "1"}, {"id": "2"}],
                        "FAOR_FLOT": {"FLOT": [{"id": "FLOT_1"}]},
                    },
                    "WYPT": {"terrain": "Syria"},
                },
            }
        },
    )

    summaries = inspect_miz_dtc(miz)

    assert len(summaries) == 1
    summary = summaries[0]
    assert summary.archive_name == "DTC/FA-18C Lot 20 DTC_1.dtc"
    assert summary.top_level_type == "FA-18C_hornet"
    assert summary.data_terrain == "Syria"
    assert summary.wypt_terrain == "Syria"
    assert summary.mez_count == 1
    assert summary.cap_count == 2
    assert summary.flot_count == 1


def test_diff_miz_dtc_reports_value_changes(tmp_path: Path) -> None:
    left = tmp_path / "left.miz"
    right = tmp_path / "right.miz"
    _write_miz(
        left,
        {
            "DTC/F-16CM bl.50 DTC_1.dtc": {
                "name": "F-16CM bl.50 DTC_1",
                "type": "F-16C_50",
                "data": {
                    "name": "",
                    "type": "F-16C_50",
                    "terrain": "Caucasus",
                    "MPD": {
                        "terrain": "Caucasus",
                        "THREAT_PTS": [{"radius": 37040}],
                    },
                },
            }
        },
    )
    _write_miz(
        right,
        {
            "DTC/F-16CM bl.50 DTC_1.dtc": {
                "name": "F-16CM bl.50 DTC_1",
                "type": "F-16C_50",
                "data": {
                    "name": "",
                    "type": "F-16C_50",
                    "terrain": "Syria",
                    "MPD": {
                        "terrain": "Syria",
                        "THREAT_PTS": [{"radius": 18520}],
                    },
                },
            }
        },
    )

    diffs = diff_miz_dtc(left, right)

    assert (
        "DTC/F-16CM bl.50 DTC_1.dtc.data.MPD.THREAT_PTS[0].radius: 37040 != 18520"
        in diffs
    )
    assert "DTC/F-16CM bl.50 DTC_1.dtc.data.terrain: 'Caucasus' != 'Syria'" in diffs
