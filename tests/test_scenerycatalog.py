"""Unit tests for the shared scenery-catalog core (game/campaignloader/scenerycatalog.py).

Pure-Python; no theater/pydcs needed. Covers the behavior the emitter CLI and the
runtime importer both rely on: category mapping, grid clustering, member capping,
centroid/radius, the region_fn hook, and CSV loading.
"""

from __future__ import annotations

import csv

from game.campaignloader.scenerycatalog import (
    BUILD_CAP,
    CLUSTER_CELL,
    Building,
    categorize,
    cluster,
    load_buildings_from_csv,
)


def _b(typ: str, x: float, z: float) -> Building:
    return Building(oid="x", typ=typ, x=x, z=z)


def test_categorize_known_families() -> None:
    assert categorize("INDUSTRIAL_EU_04") == "factory"
    assert categorize("TRANSFORMER_BOOTH_USSR") == "power"
    assert categorize("SAFSAIRBASE_WAREHOUSE_01") == "ware"
    assert categorize("SILO_03") == "ware"
    assert categorize("AIRBASE_ANTENNA_01") == "comms"
    assert categorize("RW_TOWER_EU") == "comms"
    assert categorize("WEATHER_STATION") == "comms"


def test_categorize_case_insensitive_and_unknown() -> None:
    assert categorize("industrial_garage") == "factory"
    # residential noise / anything unmapped is dropped
    assert categorize("GERMAN_CITY_HOUSE_03") is None
    assert categorize("BERLIN_WALL_01") is None


def test_cluster_merges_adjacent_splits_distant() -> None:
    # Two buildings in the same/adjacent cell merge; one far away is its own cluster.
    near_a = _b("INDUSTRIAL_EU_01", 0.0, 0.0)
    near_b = _b("INDUSTRIAL_EU_02", CLUSTER_CELL * 0.5, 0.0)  # same cell-ish neighbour
    far = _b("INDUSTRIAL_EU_03", CLUSTER_CELL * 50, CLUSTER_CELL * 50)
    clusters = cluster([near_a, near_b, far], "factory")
    assert len(clusters) == 2
    sizes = sorted(c.n for c in clusters)
    assert sizes == [1, 2]


def test_cluster_centroid_and_radius() -> None:
    a = _b("INDUSTRIAL_EU_01", 0.0, 0.0)
    b = _b("INDUSTRIAL_EU_02", 100.0, 0.0)  # within one cell-neighbour of a
    [c] = cluster([a, b], "factory")
    assert c.n == 2
    assert c.cx == 50.0
    assert c.cz == 0.0
    # radius = RADIUS_MARGIN + max member distance from centroid (50 m here)
    assert c.radius > 50.0


def test_build_cap_limits_members() -> None:
    # A dense line of > BUILD_CAP buildings in touching cells forms one capped cluster.
    blds = [
        _b("INDUSTRIAL_EU_01", i * (CLUSTER_CELL * 0.5), 0.0)
        for i in range(BUILD_CAP + 10)
    ]
    [c] = cluster(blds, "factory")
    assert c.n == BUILD_CAP


def test_region_fn_tags_clusters() -> None:
    a = _b("INDUSTRIAL_EU_01", 0.0, 0.0)
    [c] = cluster([a], "factory", region_fn=lambda x, z: "Berlin")
    assert c.region == "Berlin"


def test_region_default_without_fn() -> None:
    [c] = cluster([_b("INDUSTRIAL_EU_01", 0.0, 0.0)], "factory")
    assert c.region == "other"


def test_load_buildings_from_csv(tmp_path) -> None:  # type: ignore[no-untyped-def]
    p = tmp_path / "dump.csv"
    with open(p, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["id", "type", "life0", "x", "z", "y", "lat", "lon", "mgrs"])
        w.writerow(
            [
                "1",
                "INDUSTRIAL_EU_04",
                "200",
                "-226319.13",
                "-489069.03",
                "44.9",
                "",
                "",
                "",
            ]
        )
        w.writerow(
            [
                "2",
                "TRANSFORMER_BOOTH_USSR",
                "50",
                "-228161.85",
                "-490190.88",
                "39.9",
                "",
                "",
                "",
            ]
        )
        w.writerow(
            ["3", "GERMAN_CITY_HOUSE_01", "150", "-220000", "-480000", "40", "", "", ""]
        )
    by_cat = load_buildings_from_csv(str(p))
    assert set(by_cat) == {"factory", "power"}  # residential row dropped
    assert by_cat["factory"][0].oid == "1"
    assert by_cat["factory"][0].x == -226319.13
    assert by_cat["power"][0].typ == "TRANSFORMER_BOOTH_USSR"
