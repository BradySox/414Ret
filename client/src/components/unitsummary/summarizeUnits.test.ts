import summarizeUnits from "./summarizeUnits";

it("strips unit id prefixes and collapses duplicates with counts", () => {
  expect(
    summarizeUnits([
      "0812 | M92 Sandbag 05",
      "0813 | M92 Sandbag 05",
      "0814 | M92 Tent 01",
    ])
  ).toEqual(["2x M92 Sandbag 05", "M92 Tent 01"]);
});

it("counts dead units apart from alive ones", () => {
  expect(
    summarizeUnits(["0001 | SNR_75V", "0002 | SNR_75V [DEAD]"])
  ).toEqual(["SNR_75V", "SNR_75V [DEAD]"]);
});

it("preserves the server's unit order", () => {
  expect(
    summarizeUnits(["0001 | Track Radar", "0002 | Launcher", "0003 | Launcher"])
  ).toEqual(["Track Radar", "2x Launcher"]);
});

it("caps a long list with an and-more tail", () => {
  const units = Array.from({ length: 20 }, (_, i) => `${i} | Type ${i}`);
  const lines = summarizeUnits(units, 5);
  expect(lines).toHaveLength(6);
  expect(lines[5]).toEqual("…and 15 more");
});

it("passes unprefixed names through unchanged", () => {
  expect(summarizeUnits(["Admiral Kuznetsov"])).toEqual(["Admiral Kuznetsov"]);
});
