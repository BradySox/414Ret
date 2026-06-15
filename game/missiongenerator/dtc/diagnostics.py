"""Helpers for inspecting native DTC cartridges inside ``.miz`` archives."""

from __future__ import annotations

import json
import zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterator


@dataclass(frozen=True)
class CartridgeSummary:
    archive_name: str
    compression: str
    compress_size: int
    file_size: int
    top_level_name: str
    top_level_type: str
    data_name: str
    data_type: str
    data_terrain: str
    wypt_terrain: str | None
    mpd_terrain: str | None
    threat_count: int
    mez_count: int
    cap_count: int
    flot_count: int

    @classmethod
    def from_archive_entry(
        cls, info: zipfile.ZipInfo, cartridge: dict[str, Any]
    ) -> CartridgeSummary:
        data = _dict_value(cartridge, "data")
        wypt = _dict_value(data, "WYPT")
        mpd = _dict_value(data, "MPD")
        sa = _dict_value(data, "SA")
        faor_flot = _dict_value(sa, "FAOR_FLOT")
        flot = _list_value(faor_flot, "FLOT")
        return cls(
            archive_name=info.filename,
            compression=_compression_name(info.compress_type),
            compress_size=info.compress_size,
            file_size=info.file_size,
            top_level_name=_str_value(cartridge, "name"),
            top_level_type=_str_value(cartridge, "type"),
            data_name=_str_value(data, "name"),
            data_type=_str_value(data, "type"),
            data_terrain=_str_value(data, "terrain"),
            wypt_terrain=_optional_str_value(wypt, "terrain"),
            mpd_terrain=_optional_str_value(mpd, "terrain"),
            threat_count=len(_list_value(mpd, "THREAT_PTS")),
            mez_count=len(_list_value(sa, "MEZ_THRTS")),
            cap_count=len(_list_value(sa, "CAP_PTS")),
            flot_count=len(flot),
        )


def inspect_miz_dtc(miz_path: Path) -> list[CartridgeSummary]:
    """Return one summary per ``DTC/*.dtc`` member in ``miz_path``."""
    summaries: list[CartridgeSummary] = []
    with zipfile.ZipFile(miz_path) as miz:
        for info in sorted(miz.infolist(), key=lambda i: i.filename):
            if not _is_dtc_member(info.filename):
                continue
            cartridge = json.loads(miz.read(info.filename))
            if not isinstance(cartridge, dict):
                raise TypeError(f"{info.filename} does not contain a JSON object")
            summaries.append(CartridgeSummary.from_archive_entry(info, cartridge))
    return summaries


def diff_miz_dtc(left_miz: Path, right_miz: Path, limit: int = 80) -> list[str]:
    """Return a compact JSON diff of the DTC members inside two ``.miz`` archives."""
    left = _load_dtc_members(left_miz)
    right = _load_dtc_members(right_miz)
    diffs: list[str] = []

    left_only = sorted(set(left) - set(right))
    right_only = sorted(set(right) - set(left))
    for name in left_only:
        diffs.append(f"only in {left_miz.name}: {name}")
    for name in right_only:
        diffs.append(f"only in {right_miz.name}: {name}")

    for name in sorted(set(left) & set(right)):
        _diff_json(left[name], right[name], name, diffs, limit)
        if len(diffs) >= limit:
            break
    return diffs[:limit]


def _load_dtc_members(miz_path: Path) -> dict[str, Any]:
    with zipfile.ZipFile(miz_path) as miz:
        return {
            info.filename: json.loads(miz.read(info.filename))
            for info in miz.infolist()
            if _is_dtc_member(info.filename)
        }


def _diff_json(left: Any, right: Any, path: str, diffs: list[str], limit: int) -> None:
    if len(diffs) >= limit:
        return
    if type(left) is not type(right):
        diffs.append(
            f"{path}: type mismatch {type(left).__name__} != {type(right).__name__}"
        )
        return
    if isinstance(left, dict):
        left_keys = set(left)
        right_keys = set(right)
        for key in sorted(left_keys - right_keys):
            diffs.append(f"{path}.{key}: only on left")
            if len(diffs) >= limit:
                return
        for key in sorted(right_keys - left_keys):
            diffs.append(f"{path}.{key}: only on right")
            if len(diffs) >= limit:
                return
        for key in sorted(left_keys & right_keys):
            _diff_json(left[key], right[key], f"{path}.{key}", diffs, limit)
            if len(diffs) >= limit:
                return
        return
    if isinstance(left, list):
        if len(left) != len(right):
            diffs.append(f"{path}: length {len(left)} != {len(right)}")
            if len(diffs) >= limit:
                return
        for idx, (left_item, right_item) in enumerate(zip(left, right)):
            _diff_json(left_item, right_item, f"{path}[{idx}]", diffs, limit)
            if len(diffs) >= limit:
                return
        return
    if left != right:
        diffs.append(f"{path}: {left!r} != {right!r}")


def _is_dtc_member(filename: str) -> bool:
    return filename.startswith("DTC/") and filename.endswith(".dtc")


def _compression_name(compress_type: int) -> str:
    names = {
        zipfile.ZIP_STORED: "stored",
        zipfile.ZIP_DEFLATED: "deflated",
        zipfile.ZIP_BZIP2: "bzip2",
        zipfile.ZIP_LZMA: "lzma",
    }
    return names.get(compress_type, str(compress_type))


def _dict_value(mapping: dict[str, Any], key: str) -> dict[str, Any]:
    value = mapping.get(key, {})
    if isinstance(value, dict):
        return value
    return {}


def _list_value(mapping: dict[str, Any], key: str) -> list[Any]:
    value = mapping.get(key, [])
    if isinstance(value, list):
        return value
    return []


def _str_value(mapping: dict[str, Any], key: str) -> str:
    value = mapping.get(key, "")
    return value if isinstance(value, str) else ""


def _optional_str_value(mapping: dict[str, Any], key: str) -> str | None:
    if key not in mapping:
        return None
    value = mapping[key]
    return value if isinstance(value, str) else None


def format_summaries(summaries: list[CartridgeSummary]) -> Iterator[str]:
    if not summaries:
        yield "No DTC cartridges found."
        return
    for summary in summaries:
        yield (
            f"{summary.archive_name}: type={summary.top_level_type}, "
            f"name={summary.top_level_name!r}, data.type={summary.data_type}, "
            f"data.terrain={summary.data_terrain!r}, WYPT.terrain={summary.wypt_terrain!r}, "
            f"MPD.terrain={summary.mpd_terrain!r}, THREAT_PTS={summary.threat_count}, "
            f"MEZ_THRTS={summary.mez_count}, CAP_PTS={summary.cap_count}, "
            f"FLOT={summary.flot_count}, compression={summary.compression}, "
            f"sizes={summary.compress_size}/{summary.file_size}"
        )
