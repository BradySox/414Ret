import LocationTooltipText from "./LocationTooltipText";
import { render, screen } from "@testing-library/react";

describe("LocationTooltipText supply status", () => {
  it("says nothing when the base is supplied", () => {
    // §90 rung A's normal state. A line on every friendly base every turn is
    // noise; the tooltip must stay quiet unless something costs the player.
    render(<LocationTooltipText name="Ramstein" supplyStatus="SUPPLIED" />);

    expect(screen.queryByText(/Cut off/)).not.toBeInTheDocument();
    expect(screen.queryByText(/Air resupply/)).not.toBeInTheDocument();
  });

  it("says nothing for an enemy base, which reports no status", () => {
    render(<LocationTooltipText name="H3" supplyStatus={null} />);

    expect(screen.queryByText(/Cut off/)).not.toBeInTheDocument();
  });

  it("warns when the base is cut off", () => {
    render(<LocationTooltipText name="Fulda" supplyStatus="ISOLATED" />);

    expect(screen.getByText(/Cut off/)).toBeInTheDocument();
  });

  it("warns when the base is on air resupply only", () => {
    render(<LocationTooltipText name="Fulda" supplyStatus="AIRLIFTED" />);

    expect(screen.getByText(/Air resupply only/)).toBeInTheDocument();
  });

  it("ignores a status it does not recognise rather than rendering a raw enum", () => {
    // A tier added server-side must not leak "SOME_NEW_STATE" into the tooltip.
    render(<LocationTooltipText name="Fulda" supplyStatus="SOME_NEW_STATE" />);

    expect(screen.queryByText(/SOME_NEW_STATE/)).not.toBeInTheDocument();
  });

  it("still shows the name and comms alongside a warning", () => {
    render(
      <LocationTooltipText
        name="Fulda"
        tacan="74X"
        atcFrequency="251.0 MHz"
        supplyStatus="ISOLATED"
      />
    );

    expect(screen.getByText("Fulda")).toBeInTheDocument();
    expect(screen.getByText(/74X/)).toBeInTheDocument();
    expect(screen.getByText(/Cut off/)).toBeInTheDocument();
  });
});
