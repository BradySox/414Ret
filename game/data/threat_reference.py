"""Curated air-defence reference data for the Threat Intel Brief kneeboard.

Retribution knows a site's *live* numbers (engagement/detection range, HARM ALIC
code, alive/dead) but not the doctrinal characteristics a real intelligence
briefing carries — guidance type, engagement ceiling, and how to defeat the
system. This module supplies that curated layer, keyed by the DCS air-defence
unit id of a system's radar/launcher (the same ids ``AlicCodes`` uses). A site is
matched by scanning its units, so any one of a system's coded units resolves the
reference. Systems without an entry fall back to live data only.

Content is general, publicly-documented system characteristics — deliberately
concise to fit a kneeboard card. Ceilings are approximate engagement ceilings in
feet.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Optional

from dcs.vehicles import AirDefence


@dataclass(frozen=True)
class ThreatReference:
    guidance: str
    ceiling_ft: Optional[int]
    defeat: str


# Reusable references shared by every coded unit id of a system (radar + launcher
# both point at the same entry, so the lookup hits regardless of which unit the
# site reports).
_SA2 = ThreatReference(
    "Command radar (Fan Song)",
    88000,
    "Long reach but slow, single-target and easy to defeat kinematically: drag it "
    "cold then notch/dive, or mask in terrain. SEAD with HARM from outside the ring "
    "— the Fan Song is fragile once located.",
)
_SA3 = ThreatReference(
    "Command radar (Low Blow)",
    59000,
    "Short-legged and low-altitude; outrange it and it can't touch you. Notch the "
    "Low Blow or terrain-mask; HARM the radar. Often co-located with an SA-2.",
)
_SA6 = ThreatReference(
    "Semi-active radar (Straight Flush)",
    40000,
    "Lethal in the heart of its ring and highly mobile — assume it moved. Stay low "
    "in terrain on ingress and pop for the shot, or stand off with HARM/standoff "
    "PGMs. Defeat a launch by notching beam-on and diving.",
)
_SA8 = ThreatReference(
    "Command radar, self-contained",
    16000,
    "Mobile, quick-reacting, short range. Stay above ~16,000 ft or outside ~6 nm. "
    "Spoofs poorly — chaff + a hard beam/dive notch breaks the track; HARM works "
    "but the small radar relocates fast.",
)
_SA10 = ThreatReference(
    "Track-via-missile (Big Bird / Flap Lid)",
    90000,
    "Strategic, very long range and high ceiling — do NOT enter the ring without "
    "dedicated SEAD. Standoff PGMs / cruise the radars, or route around. Inside the "
    "ring, last-ditch: drag to bleed the missile then notch beam-on at low altitude.",
)
_SA11 = ThreatReference(
    "Semi-active radar (Snow Drift / Fire Dome)",
    72000,
    "Fast, long-range and mobile — a top SEAD priority. Stand off outside ~20 nm and "
    "HARM the Snow Drift; if engaged, notch beam-on and dive hard. Each TELAR can "
    "guide independently, so suppression must be thorough.",
)
_SA13 = ThreatReference(
    "IR-homing (passive)",
    11500,
    "No radar to warn you or HARM — visual/IR only. Stay above ~12,000 ft or outside "
    "~4 nm; flares + a beam turn defeat a shot. Treat as a pop-up; kill with "
    "standoff PGMs or guns once located.",
)
_SA15 = ThreatReference(
    "Command radar, self-contained",
    20000,
    "Very mobile and quick — designed to kill PGMs as well as aircraft. Don't loiter "
    "in the ring. Saturate or stand off with HARM/standoff weapons; a hard beam/dive "
    "notch can defeat a single shot.",
)
_SA19 = ThreatReference(
    "Radar SACLOS + IR, guns & missiles",
    11500,
    "Dual missile+gun threat, radar-directed and very mobile. Stay above ~12,000 ft "
    "and outside ~5 nm — deadly down low. Notch the radar and flare; standoff PGMs "
    "from altitude.",
)
_SA9 = ThreatReference(
    "IR-homing (passive)",
    11000,
    "Passive IR, no warning — visual only. Stay high/standoff; flares + a beam turn "
    "defeat the shot.",
)
_SA5 = ThreatReference(
    "Command / SARH radar (Square Pair)",
    95000,
    "Very long range and high ceiling, but a big, slow missile with a long flyout — "
    "a SEAD problem, not a maneuver one. Stay out of the ring or HARM the Square Pair "
    "from standoff; if shot at, drag to bleed it then notch beam-on low.",
)
_MANPAD = ThreatReference(
    "IR-homing, man-portable (passive)",
    11000,
    "No radar warning — pure IR, and everywhere near the front line. Stay above "
    "~10,000 ft over troops; flares plus a beam turn defeat a shot. HARM can't touch "
    "it — just deny it the low, slow pass.",
)
_SHILKA = ThreatReference(
    "Radar-directed AAA (Gun Dish)",
    8000,
    "Radar-laid 23 mm — murderous below ~8,000 ft, harmless above it. Simply stay "
    "high; if you must go low, jink and don't fly predictable strafe passes.",
)
_GEPARD = ThreatReference(
    "Radar-directed AAA",
    9000,
    "Accurate twin 35 mm to ~9,000 ft. Stay above it; avoid straight, level "
    "low-altitude passes within ~3 nm.",
)
_ROLAND = ThreatReference(
    "Command radar / EO",
    18000,
    "Short-range point defence, quick-reacting. Stay above ~18,000 ft or outside "
    "~6 nm; chaff + beam notch the radar version. Often guards high-value targets.",
)
_HAWK = ThreatReference(
    "Semi-active radar (High Power)",
    45000,
    "Long-range Western SAM — respect the ring. HARM the High Power / CWAR radars "
    "from standoff; if engaged, notch beam-on and dive. Less mobile than Soviet kit.",
)
_PATRIOT = ThreatReference(
    "Track-via-missile",
    80000,
    "Strategic, very long range/high ceiling — route around or dedicate SEAD. Not a "
    "threat you defeat by maneuver inside the ring; stay out of it.",
)
_NASAMS = ThreatReference(
    "Active radar (AMRAAM)",
    50000,
    "Fire-and-forget AMRAAM shots — no SARH to notch through the whole flyout. Deny "
    "the track: stay outside ~15 nm, drag/notch the active missile late, kill the "
    "MPQ-64 radar with HARM/standoff.",
)
_RAPIER = ThreatReference(
    "SACLOS (optical / Blindfire radar)",
    10000,
    "Short-range point defence; the optical version gives no RWR warning. Stay above "
    "~10,000 ft or outside ~4 nm; HARM only bites the Blindfire-radar variant.",
)
_EWR = ThreatReference(
    "Early-warning search radar",
    None,
    "No weapons — but it cues the whole IADS. Kill it (HARM-targetable) to blind the "
    "network, or stay below its radar horizon by flying low.",
)
_DOG_EAR = ThreatReference(
    "SHORAD search radar",
    None,
    "Acquisition radar that cues short-range SAMs — no weapon of its own. Killing it "
    "blinds the SHORAD it feeds.",
)


THREAT_REFERENCE: Dict[str, ThreatReference] = {
    AirDefence.SNR_75V.id: _SA2,
    AirDefence.snr_s_125_tr.id: _SA3,
    AirDefence.p_19_s_125_sr.id: _SA3,
    AirDefence.RPC_5N62V.id: _SA5,
    AirDefence.Kub_1S91_str.id: _SA6,
    AirDefence.Osa_9A33_ln.id: _SA8,
    AirDefence.S_300PS_40B6M_tr.id: _SA10,
    AirDefence.S_300PS_40B6MD_sr.id: _SA10,
    AirDefence.S_300PS_64H6E_sr.id: _SA10,
    AirDefence.SA_11_Buk_LN_9A310M1.id: _SA11,
    AirDefence.SA_11_Buk_SR_9S18M1.id: _SA11,
    AirDefence.Strela_10M3.id: _SA13,
    AirDefence.Strela_1_9P31.id: _SA9,
    AirDefence.Tor_9A331.id: _SA15,
    AirDefence.x_2S6_Tunguska.id: _SA19,
    AirDefence.ZSU_23_4_Shilka.id: _SHILKA,
    AirDefence.Gepard.id: _GEPARD,
    AirDefence.Roland_ADS.id: _ROLAND,
    AirDefence.Roland_Radar.id: _ROLAND,
    AirDefence.Hawk_tr.id: _HAWK,
    AirDefence.Hawk_sr.id: _HAWK,
    AirDefence.Hawk_cwar.id: _HAWK,
    AirDefence.Patriot_str.id: _PATRIOT,
    AirDefence.NASAMS_Radar_MPQ64F1.id: _NASAMS,
    AirDefence.rapier_fsa_launcher.id: _RAPIER,
    AirDefence.rapier_fsa_blindfire_radar.id: _RAPIER,
    AirDefence.x_1L13_EWR.id: _EWR,
    AirDefence.x_55G6_EWR.id: _EWR,
    AirDefence.RLS_19J6.id: _EWR,
    AirDefence.Dog_Ear_radar.id: _DOG_EAR,
    AirDefence.SA_18_Igla_manpad.id: _MANPAD,
    AirDefence.SA_18_Igla_S_manpad.id: _MANPAD,
    AirDefence.Igla_manpad_INS.id: _MANPAD,
    AirDefence.Soldier_stinger.id: _MANPAD,
}


def reference_for(unit_type_id: str) -> Optional[ThreatReference]:
    """Curated reference for a DCS air-defence unit id, or None if uncatalogued."""
    return THREAT_REFERENCE.get(unit_type_id)
