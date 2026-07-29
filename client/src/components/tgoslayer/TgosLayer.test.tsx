import { Tgo } from "../../api/liberationApi";
import { renderWithProviders } from "../../testutils";
import TgosLayer from "./TgosLayer";
import { PropsWithChildren } from "react";

const mockTgo = jest.fn();
jest.mock("react-leaflet", () => ({
  LayerGroup: (props: PropsWithChildren<any>) => <>{props.children}</>,
}));
jest.mock("../tgos/Tgo", () => (props: any) => {
  mockTgo(props.tgo);
  return null;
});

function tgo(id: string, category: string, task: string | null): Tgo {
  return {
    id,
    name: id,
    control_point_name: "Bar",
    category,
    blue: false,
    position: { lat: 0, lng: 0 },
    units: [],
    threat_ranges: [],
    detection_ranges: [],
    dead: false,
    sidc: "10061000001301000000",
    // GroupTask is a tuple-valued enum, so it serializes as [name, role].
    task: task === null ? undefined : [task, "AntiAir"],
    mobile: false,
    user_placed: false,
  };
}

const WORLD = [
  tgo("lorad-site", "aa", "LORAD"),
  tgo("merad-site", "aa", "MERAD"),
  tgo("shorad-site", "aa", "SHORAD"),
  tgo("taskless-site", "aa", null),
  tgo("armor-group", "armor", "FrontLine"),
];

function render(props: Parameters<typeof TgosLayer>[0]) {
  renderWithProviders(<TgosLayer {...props} />, {
    preloadedState: {
      tgos: {
        tgos: Object.fromEntries(WORLD.map((t) => [t.id, t])),
      },
    },
  });
  return mockTgo.mock.calls.map((call) => call[0].id).sort();
}

beforeEach(() => mockTgo.mockClear());

describe("TgosLayer", () => {
  it("draws every TGO of the category when no task filter is set", () => {
    // The "Air defences" master with no class row ticked.
    expect(render({ categories: ["aa"] })).toEqual([
      "lorad-site",
      "merad-site",
      "shorad-site",
      "taskless-site",
    ]);
  });

  it("narrows to the requested tasks", () => {
    expect(render({ categories: ["aa"], tasks: ["LORAD", "SHORAD"] })).toEqual([
      "lorad-site",
      "shorad-site",
    ]);
  });

  it("excludes a task-less TGO while a task filter is active", () => {
    // Regression: the old filter returned on the task check alone, so a task-less
    // `aa` site fell through to the category check and drew a duplicate marker in
    // every one of the four class layers at once.
    expect(render({ categories: ["aa"], tasks: ["LORAD"] })).not.toContain(
      "taskless-site"
    );
  });

  it("enforces the category even when the task matches", () => {
    expect(render({ categories: ["armor"], tasks: ["LORAD"] })).toEqual([]);
  });

  it("honours the exclude flag", () => {
    expect(render({ categories: ["aa", "factory", "ship"], exclude: true })).toEqual(
      ["armor-group"]
    );
  });
});
