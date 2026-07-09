import { selectCampaignStatus } from "../../api/campaignStatusSlice";
import { useAppSelector } from "../../app/hooks";
import "./CampaignStatusBar.css";
import { useState } from "react";

// The campaign-status ribbon (campaign phases W3): a slim bar above the map with
// the campaign name, turn, date, the inferred phase + its "why" string, and — on
// Vietnam campaigns — the political-will meters. Renders nothing when no game is
// loaded; each segment self-hides when its data is absent (phases off, will off),
// so the ribbon degrades gracefully to just "campaign · turn · date".
//
// Clicking the phase chip unfolds the ARC EXPANDER: the campaign's whole phase
// sequence with schedule, locked target classes, and sanctuaries, plus the
// political-will history sparkline — "where am I in the war, and what may I hit."
//
// It floats over the Leaflet map as a plain positioned div (NOT a Leaflet
// control/layer, so the map-layer tests and z-index stack are untouched).

function WillSparkline(props: { history: [number, number, number][] }) {
  if (props.history.length < 2) {
    return null;
  }
  const width = 220;
  const height = 44;
  const points = props.history;
  const x = (i: number) => (i / (points.length - 1)) * (width - 4) + 2;
  const y = (will: number) => height - 3 - (will / 100) * (height - 6);
  const path = (idx: 1 | 2) =>
    points.map((p, i) => `${i === 0 ? "M" : "L"}${x(i)},${y(p[idx])}`).join(" ");
  return (
    <svg
      width={width}
      height={height}
      className="campaign-status-sparkline"
      aria-label="Political will history"
    >
      <line x1="2" y1={y(50)} x2={width - 2} y2={y(50)} className="spark-mid" />
      <path d={path(1)} className="spark-blue" />
      <path d={path(2)} className="spark-red" />
    </svg>
  );
}

export default function CampaignStatusBar() {
  const status = useAppSelector(selectCampaignStatus);
  const [expanded, setExpanded] = useState(false);
  if (status == null) {
    return null;
  }
  // Parse the ISO campaign date as LOCAL, not UTC: `new Date("1968-07-15")`
  // is UTC midnight, which toLocaleDateString renders as Jul 14 in any
  // western-hemisphere zone -- the ribbon showed the day before the game date.
  const [y, m, d] = status.date.split("-").map(Number);
  const dateText =
    y && m && d
      ? new Date(y, m - 1, d).toLocaleDateString(undefined, {
          year: "numeric",
          month: "short",
          day: "numeric",
        })
      : status.date;
  const phases = status.phases ?? [];
  const history = status.will_history ?? [];
  const expandable = phases.length > 0;
  return (
    <div className="campaign-status-wrap">
      <div className="campaign-status-bar" title={status.phase_narrative ?? ""}>
        <span className="campaign-status-name">
          {status.campaign_name ?? "Campaign"}
        </span>
        <span className="campaign-status-item">Turn {status.turn}</span>
        <span className="campaign-status-item">{dateText}</span>
        {status.phase_status != null && (
          <span
            className={
              "campaign-status-phase" + (expandable ? " expandable" : "")
            }
            onClick={() => expandable && setExpanded(!expanded)}
            title={
              expandable
                ? "Click for the campaign's phase arc"
                : status.phase_narrative ?? ""
            }
          >
            {status.phase_status}
            {expandable && (
              <span className="campaign-status-caret">
                {expanded ? " ▴" : " ▾"}
              </span>
            )}
          </span>
        )}
        {status.red_posture != null && (
          <span
            className={
              "campaign-status-posture posture-" +
              status.red_posture.toLowerCase()
            }
            title={
              status.red_posture_detail ??
              "The enemy commander's current posture"
            }
          >
            ENEMY {status.red_posture}
          </span>
        )}
        {status.blue_will != null && (
          <span
            className="campaign-status-will campaign-status-will-blue"
            title={
              status.blue_will_note
                ? `Last turn ${status.blue_will_note}`
                : (status.blue_will_label ?? "Washington's political will")
            }
          >
            WILL {Math.round(status.blue_will)}
          </span>
        )}
        {status.red_will != null && (
          <span
            className="campaign-status-will campaign-status-will-red"
            title={
              status.red_will_note
                ? `Last turn ${status.red_will_note}`
                : (status.red_will_label ?? "Hanoi's regime resolve")
            }
          >
            RESOLVE {Math.round(status.red_will)}
          </span>
        )}
      </div>
      {expanded && (
        <div className="campaign-status-panel">
          {phases.map((phase, idx) => (
            <div
              key={phase.key}
              className={
                "campaign-phase-row" + (phase.current ? " current" : "")
              }
            >
              <div className="campaign-phase-head">
                <span className="campaign-phase-index">{idx + 1}</span>
                <span className="campaign-phase-name">{phase.name}</span>
                <span className="campaign-phase-when">
                  {phase.current
                    ? "now"
                    : phase.min_turn > 0
                      ? `~turn ${phase.min_turn}`
                      : idx === 0
                        ? "opening"
                        : "adaptive"}
                </span>
              </div>
              <div className="campaign-phase-body">
                {phase.narrative && (
                  <div className="campaign-phase-narrative">
                    {phase.narrative}
                  </div>
                )}
                {phase.objectives.length > 0 && (
                  <ul className="campaign-phase-objectives">
                    {phase.objectives.map((objective, oidx) => (
                      <li
                        key={oidx}
                        className={
                          objective.done == null
                            ? "objective-info"
                            : objective.done
                              ? "objective-done"
                              : "objective-open"
                        }
                      >
                        <span className="objective-tick">
                          {objective.done == null
                            ? "•"
                            : objective.done
                              ? "✓"
                              : "○"}
                        </span>
                        {objective.text}
                      </li>
                    ))}
                  </ul>
                )}
                <div className="campaign-phase-rules">
                  {phase.locked.length > 0 ? (
                    <span>
                      Locked: {phase.locked.join(", ")} — everything else (AAA,
                      armor, troops, trucks on the road) is fair game.
                    </span>
                  ) : (
                    <span>No target classes locked.</span>
                  )}
                  {phase.zones.length > 0 && (
                    <span> Sanctuary: {phase.zones.join(", ")}.</span>
                  )}
                </div>
                {phase.advance && (
                  <div className="campaign-phase-advance">{phase.advance}.</div>
                )}
              </div>
            </div>
          ))}
          {history.length >= 2 && (
            <div className="campaign-status-panel-will">
              <span className="campaign-status-panel-will-label">
                Will over time
              </span>
              <WillSparkline history={history} />
            </div>
          )}
          {(status.blue_will_note || status.red_will_note) && (
            <div className="campaign-status-panel-notes">
              {status.blue_will_note && (
                <div className="will-note will-note-blue">
                  WILL last turn {status.blue_will_note}
                </div>
              )}
              {status.red_will_note && (
                <div className="will-note will-note-red">
                  RESOLVE last turn {status.red_will_note}
                </div>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
