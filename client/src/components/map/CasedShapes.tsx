import {
  StrokeSignature,
  mapColors,
} from "../../theme/mapColors";
import type { LeafletEventHandlerFnMap, PathOptions } from "leaflet";
import { ComponentProps, ReactNode } from "react";
import { Circle, CircleMarker, Polygon } from "react-leaflet";

/* Cased (haloed) map shapes — the shared contrast treatment for the dashed
   overlay family. A bright dashed stroke alone disappears into light satellite
   imagery (the flown Iraq map washed the amber suspected circles out entirely),
   so each shape is drawn twice: a wider dark dash (mapColors.strokeCasing)
   underneath, then the category colour on top, same geometry + dashArray so the
   dashes align. The dark edge carries the shape on light terrain, the colour on
   dark — the classic cartographic halo. The casing is never interactive; the
   top shape owns the tooltip/click contract. Which pattern a category uses is
   its StrokeSignature (mapStrokes) — the unique look that keeps an area, a
   zone, a hazard, and a person decodable without the legend. */

interface CasedStyle {
  color: string;
  signature: StrokeSignature;
  /** Defaults to `color`. */
  fillColor?: string;
  /** Omit for an unfilled outline. */
  fillOpacity?: number;
  className?: string;
}

export function casingOptions(signature: StrokeSignature): PathOptions {
  return {
    color: signature.casingColor ?? mapColors.strokeCasing,
    weight: signature.casingWeight,
    opacity: 0.75,
    dashArray: signature.dashArray,
    lineCap: signature.lineCap,
    fill: false,
    interactive: false,
  };
}

export function strokeOptions(style: CasedStyle): PathOptions {
  return {
    color: style.color,
    weight: style.signature.weight,
    dashArray: style.signature.dashArray,
    lineCap: style.signature.lineCap,
    fill: style.fillOpacity !== undefined,
    fillColor: style.fillColor ?? style.color,
    fillOpacity: style.fillOpacity,
    className: style.className,
  };
}

interface CasedShapeProps extends CasedStyle {
  eventHandlers?: LeafletEventHandlerFnMap;
  children?: ReactNode;
}

/** A geographic circle (radius in meters) with a contrast casing. */
export function CasedCircle(
  props: CasedShapeProps & {
    center: ComponentProps<typeof Circle>["center"];
    radius: number;
  }
) {
  return (
    <>
      <Circle
        center={props.center}
        radius={props.radius}
        pathOptions={casingOptions(props.signature)}
      />
      <Circle
        center={props.center}
        radius={props.radius}
        pathOptions={strokeOptions(props)}
        eventHandlers={props.eventHandlers}
      >
        {props.children}
      </Circle>
    </>
  );
}

/** A polygon (zone outline) with a contrast casing. */
export function CasedPolygon(
  props: CasedShapeProps & {
    positions: ComponentProps<typeof Polygon>["positions"];
  }
) {
  return (
    <>
      <Polygon
        positions={props.positions}
        pathOptions={casingOptions(props.signature)}
      />
      <Polygon
        positions={props.positions}
        pathOptions={strokeOptions(props)}
        eventHandlers={props.eventHandlers}
      >
        {props.children}
      </Polygon>
    </>
  );
}

/** A fixed-pixel-radius marker circle with a contrast casing. */
export function CasedCircleMarker(
  props: CasedShapeProps & {
    center: ComponentProps<typeof CircleMarker>["center"];
    radius: number;
  }
) {
  return (
    <>
      <CircleMarker
        center={props.center}
        radius={props.radius}
        pathOptions={casingOptions(props.signature)}
      />
      <CircleMarker
        center={props.center}
        radius={props.radius}
        pathOptions={strokeOptions(props)}
        eventHandlers={props.eventHandlers}
      >
        {props.children}
      </CircleMarker>
    </>
  );
}
