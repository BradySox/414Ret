/**
 * Shared semantic colours for the campaign map.
 *
 * The map overlays had each hardcoded their own red / amber / green, so "red"
 * meant six different things across components and two dashed-red circles read as
 * the same thing while meaning opposites. This is the single source of truth: a
 * component (and the on-map legend) decodes a colour by its *meaning*, not its hex.
 *
 * Values match the pre-existing de-facto colours so nothing shifts visually, with
 * two deliberate reconciliations from the UI audit:
 *   - SUSPECTED (a concealed, un-reconned enemy) moves OFF red onto amber, so the
 *     "go find it" uncertainty circle no longer looks like the red "do NOT strike"
 *     ROE circle (OFF_LIMITS).
 *   - ROUTE_FRIENDLY is lifted off the near-black navy that vanished on satellite
 *     imagery to a legible blue.
 */
export const mapColors = {
  // --- allegiance ---
  friendly: "#0084ff", // your forces: flight paths, threat rings
  enemy: "#c85050", // enemy forces: flight paths, threat rings
  flot: "#fe7d0a", // the front line (FLOT)

  // --- sensor coverage (SAM/EWR range rings) ---
  detectionFriendly: "#bb89ff", // violet: friendly radar detection range
  detectionEnemy: "#eee17b", // pale yellow: enemy radar detection range

  // --- intel / ROE ---
  suspected: "#dd9a3a", // amber dashed: un-reconned "suspected activity"
  offLimits: "#d43a3a", // red dashed: ROE restricted (no-strike) zone
  weaponsFree: "#3ccd5f", // green dashed: free-fire (weapons-free) pocket
  mine: "#c9a227", // gold dashed: your own air-dropped minefield (friendly hazard)

  // --- supply readiness (by level, not side) ---
  supplyOk: "#3ccd5f",
  supplyMid: "#e0b13a",
  supplyLow: "#e07a2f",
  supplyCritical: "#d43a3a",
  supplyProducer: "#4a90d9",

  // --- supply routes ---
  routeFriendly: "#4a90d9", // lifted from #2d3e50 (near-invisible on imagery)
  routeEnemy: "#8c1414",
  routeContested: "#c85050",
  routeActive: "#ffffff", // the live-transport highlight line

  // --- personnel (§21 downed aviators) ---
  pilotMia: "#ff8c2e", // rescue orange: an evader awaiting pickup (actionable)
  pilotPow: "#9aa0a6", // gray: held at an enemy field (freed by recapture)

  // --- misc ---
  highlight: "#ffff00",
} as const;

export type MapColorKey = keyof typeof mapColors;

/**
 * Shared supply-readiness banding (input is the raw supply fraction in [0, 1]).
 *
 * The ribbon chips, the map's supply nodes, and the legend must agree on what
 * each colour *means* — the ribbon used to band at 35/50 (the red-intent
 * decision thresholds) while the map banded at 85/60/50, so the same hue on the
 * two surfaces meant different numbers (2026-07-18 UI audit).
 */
export type SupplyBand = "ok" | "mid" | "low" | "critical";

export function supplyBand(fraction: number): SupplyBand {
  if (fraction >= 0.85) return "ok";
  if (fraction >= 0.6) return "mid";
  if (fraction >= 0.5) return "low";
  return "critical";
}

export function supplyBandColor(fraction: number): string {
  switch (supplyBand(fraction)) {
    case "ok":
      return mapColors.supplyOk;
    case "mid":
      return mapColors.supplyMid;
    case "low":
      return mapColors.supplyLow;
    case "critical":
      return mapColors.supplyCritical;
  }
}
