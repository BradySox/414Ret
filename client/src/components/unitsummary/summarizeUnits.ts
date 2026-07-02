// Condense a raw unit list for a hover tooltip. The server sends one entry per
// unit with a unique "0007 | " id prefix (and possibly a " [DEAD]" suffix), so
// a FOB's hundred sandbags/tents/camo nets each render as their own line and
// the tooltip fills the whole screen. Strip the id prefix, collapse duplicates
// into "12x M92 Sandbag 05" counts (dead units counted apart via their suffix),
// and cap the list with an "…and N more" tail. Insertion order is preserved so
// a SAM site still reads radar-first, launchers after, as the server ordered.
const UNIT_ID_PREFIX = /^\d+ \| /;

export const TOOLTIP_UNIT_CAP = 12;

export default function summarizeUnits(
  units: string[],
  cap: number = TOOLTIP_UNIT_CAP
): string[] {
  const counts = new Map<string, number>();
  units.forEach((unit) => {
    const name = unit.replace(UNIT_ID_PREFIX, "");
    counts.set(name, (counts.get(name) ?? 0) + 1);
  });
  const lines = Array.from(counts, ([name, n]) =>
    n > 1 ? `${n}x ${name}` : name
  );
  if (lines.length > cap) {
    return [...lines.slice(0, cap), `…and ${lines.length - cap} more`];
  }
  return lines;
}
