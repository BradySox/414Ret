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
 *   - SUSPECTED (a concealed, un-reconned enemy) uses amber, so the "go find it"
 *     uncertainty circle reads as "unknown — investigate" rather than a threat.
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

  // --- intel ---
  suspected: "#dd9a3a", // amber dashed: un-reconned "suspected activity"
  mine: "#c9a227", // gold dashed: your own air-dropped minefield (friendly hazard)
  // Dark under-stroke drawn beneath a bright dashed ring so it stays legible on
  // light terrain (desert satellite imagery washed the amber ring out entirely);
  // on dark terrain the bright dash on top still carries it.
  strokeCasing: "#141414",

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
 * A stroke signature: the dash pattern + weights that give one overlay category
 * its unique look. Colour is deliberately NOT the only channel — on desert
 * imagery (or for a colour-blind pilot) two hues can collapse into each other,
 * so every dashed-family category also differs by pattern:
 *
 *   suspected AREA   - medium dash        (something is in here, go look)
 *   minefield        - tick marks         (a hazard field, your own)
 *   pilot POW        - short dash         (held; freed by recapture)
 *   pilot MIA        - solid              (a live man, exact position)
 *
 * `casingWeight` is the dark under-stroke (strokeCasing) drawn beneath the
 * coloured dash by the CasedShapes components, so every one of these reads on
 * light and dark terrain alike.
 */
export interface StrokeSignature {
  /** SVG dash pattern; omit for a solid stroke. */
  dashArray?: string;
  weight: number;
  casingWeight: number;
  lineCap?: "round" | "butt";
}

export const mapStrokes: Record<
  "suspectedArea" | "minefield" | "pilotMia" | "pilotPow",
  StrokeSignature
> = {
  suspectedArea: { dashArray: "6 6", weight: 2.5, casingWeight: 6 },
  minefield: { dashArray: "2 8", weight: 2.5, casingWeight: 6 },
  pilotMia: { weight: 2.5, casingWeight: 6 },
  pilotPow: { dashArray: "3 5", weight: 2.5, casingWeight: 6 },
};
