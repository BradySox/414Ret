/**
 * Shared semantic colours for the campaign map.
 *
 * The map overlays had each hardcoded their own red / amber / green, so "red"
 * meant six different things across components and two dashed-red circles read as
 * the same thing while meaning opposites. This is the single source of truth: a
 * component (and the on-map legend) decodes a colour by its *meaning*, not its hex.
 *
 * Values match the pre-existing de-facto colours, with these deliberate calls:
 *   - SUSPECTED (a concealed, un-reconned enemy) is an amber dash — "unknown,
 *     investigate" — over a dark-red casing (enemy allegiance), now that dashed
 *     red is no longer reserved for the removed ROE off-limits zones; a centred
 *     "?" glyph marks it as a go-look contact. The two channels carry two facts:
 *     the red halo says "enemy", the amber dash says "we don't know where yet".
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
  suspectedCasing: "#8c1414", // dark-red halo under the amber dash: enemy, unconfirmed
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
 *   suspected AREA   - medium dash, red halo   (enemy in here somewhere, go look)
 *   suspected CLUSTER- lighter dash, red halo  (one of several stacked contacts)
 *   minefield        - tick marks              (a hazard field, your own)
 *   pilot POW        - short dash              (held; freed by recapture)
 *   pilot MIA        - solid                   (a live man, exact position)
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
  /** Casing (halo) colour; defaults to the neutral dark strokeCasing. A category
   *  overrides it to carry a second meaning in the halo — e.g. suspected-activity
   *  uses a dark-red casing so the halo reads "enemy" while the dash reads "unknown". */
  casingColor?: string;
  lineCap?: "round" | "butt";
}

export const mapStrokes: Record<
  "suspectedArea" | "suspectedCluster" | "minefield" | "pilotMia" | "pilotPow",
  StrokeSignature
> = {
  suspectedArea: {
    dashArray: "6 6",
    weight: 2.5,
    casingWeight: 6,
    casingColor: mapColors.suspectedCasing,
  },
  // A clustered member gets the SAME red-cased amber dash so it reads on
  // satellite imagery (a stroke-less fill was invisible on desert/forest tan),
  // but lighter than a lone circle — several stacked rings would otherwise ring
  // like klaxons. The stacking fill still carries the density.
  suspectedCluster: {
    dashArray: "6 6",
    weight: 2,
    casingWeight: 4.5,
    casingColor: mapColors.suspectedCasing,
  },
  minefield: { dashArray: "2 8", weight: 2.5, casingWeight: 6 },
  pilotMia: { weight: 2.5, casingWeight: 6 },
  pilotPow: { dashArray: "3 5", weight: 2.5, casingWeight: 6 },
};
