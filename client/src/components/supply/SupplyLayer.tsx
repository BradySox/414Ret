import { SupplyNode } from "../../api/liberationApi";
import { selectSupplyNodes } from "../../api/supplySlice";
import { useAppSelector } from "../../app/hooks";
import { mapColors, supplyBandColor } from "../../theme/mapColors";
import { CircleMarker, LayerGroup, Tooltip } from "react-leaflet";

// Front supply readiness -> colour (green healthy, amber strained, red starved).
// Keyed off the raw supply_factor [0,1] the server emits, through the shared
// banding so the map, the ribbon chips, and the legend all agree.
function supplyColor(supply: number): string {
  return supplyBandColor(supply);
}

// A blue "source" ring drawn under a producer node.
const PRODUCER_COLOR = mapColors.supplyProducer;

function NodeTooltip(props: { node: SupplyNode }) {
  const { node } = props;
  const pct = Math.round(node.supply * 100);
  return (
    <Tooltip sticky>
      <b>{node.name}</b>
      {node.is_front && (
        <>
          <br />
          {`Front supply: ${pct}%`}
          {node.supply < 0.5 && " — starved"}
        </>
      )}
      {node.production > 0 && (
        <>
          <br />
          {`Producer: +${Math.round(node.production)}/turn`}
        </>
      )}
    </Tooltip>
  );
}

// War-economy supply-flow overlay (§53 P4b): each BLUE control point that either
// feeds a front (coloured by materiel readiness) or produces supply (blue source
// ring). Renders nothing unless war_economy is on (the node list is empty), matching
// the restricted-zones layer. BLUE-only: enemy logistics stay fogged.
export default function SupplyLayer() {
  const nodes = useAppSelector(selectSupplyNodes);
  return (
    <LayerGroup>
      {/* Producer rings first, so a front marker sitting on a producer draws on top. */}
      {nodes
        .filter((node) => node.production > 0)
        .map((node, idx) => (
          <CircleMarker
            key={`supply-src-${node.name}-${idx}`}
            center={node.position}
            radius={13}
            color={PRODUCER_COLOR}
            weight={2}
            dashArray="4 4"
            fill={false}
          >
            <NodeTooltip node={node} />
          </CircleMarker>
        ))}
      {nodes
        .filter((node) => node.is_front)
        .map((node, idx) => {
          const color = supplyColor(node.supply);
          return (
            <CircleMarker
              key={`supply-front-${node.name}-${idx}`}
              center={node.position}
              radius={9}
              color="#ffffff"
              weight={1}
              fill={true}
              fillColor={color}
              fillOpacity={0.85}
            >
              <NodeTooltip node={node} />
            </CircleMarker>
          );
        })}
    </LayerGroup>
  );
}
