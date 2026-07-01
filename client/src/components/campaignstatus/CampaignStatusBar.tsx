import { selectCampaignStatus } from "../../api/campaignStatusSlice";
import { useAppSelector } from "../../app/hooks";
import "./CampaignStatusBar.css";

// The campaign-status ribbon (campaign phases W3): a slim bar above the map with
// the campaign name, turn, date, the inferred phase + its "why" string, and — on
// Vietnam campaigns — the political-will meters. Renders nothing when no game is
// loaded; each segment self-hides when its data is absent (phases off, will off),
// so the ribbon degrades gracefully to just "campaign · turn · date".
//
// It floats over the Leaflet map as a plain positioned div (NOT a Leaflet
// control/layer, so the map-layer tests and z-index stack are untouched).
export default function CampaignStatusBar() {
  const status = useAppSelector(selectCampaignStatus);
  if (status == null) {
    return null;
  }
  const date = new Date(status.date);
  const dateText = isNaN(date.getTime())
    ? status.date
    : date.toLocaleDateString(undefined, {
        year: "numeric",
        month: "short",
        day: "numeric",
      });
  return (
    <div className="campaign-status-bar" title={status.phase_narrative ?? ""}>
      <span className="campaign-status-name">
        {status.campaign_name ?? "Campaign"}
      </span>
      <span className="campaign-status-item">Turn {status.turn}</span>
      <span className="campaign-status-item">{dateText}</span>
      {status.phase_status != null && (
        <span className="campaign-status-phase">{status.phase_status}</span>
      )}
      {status.blue_will != null && (
        <span className="campaign-status-will campaign-status-will-blue">
          WILL {Math.round(status.blue_will)}
        </span>
      )}
      {status.red_will != null && (
        <span className="campaign-status-will campaign-status-will-red">
          RESOLVE {Math.round(status.red_will)}
        </span>
      )}
    </div>
  );
}
